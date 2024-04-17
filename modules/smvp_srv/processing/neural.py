import numpy as np
from numpy.typing import ArrayLike
import logging as log

import torch
#import torch.utils.data
from torch import nn, optim
from torch.nn import functional as F
from torchvision import datasets, transforms
import lightning as L

from .processor import *
from ..data import *
from ..utils import ti_base as tib
from ..utils.utils import logging_disabled


class NeuralRti(Processor):
    """Wrapper of the Depth-Anything framework"""
    name = "depth"
    
    def __init__(self):
        self.device = torch.device("cuda") if torch.cuda.is_available() else torch.device("cpu")
        if self.device.type == 'cuda':
            log.debug("CUDA acceleration for MiDaS enabled")
        
        self.model = None
        self.sequence = Sequence()
        

    def getDefaultSettings() -> dict:
        return {}
    
    def process(self, img_seq: Sequence, calibration: Calibration, settings: dict):
        self.sequence = Sequence()
        
        # Init model
        model = RtiAutoencoder(len(img_seq))

        # Build input / training tensor
        # Transformations applied on each image => only make them a tensor
        transform = transforms.Compose([transforms.ToTensor(), transforms.Normalize((0.5,), (0.5,))])

        # Loading the training dataset. We need to split it into a training and validation part
        train_dataset = CIFAR10(root=DATASET_PATH, train=True, transform=transform, download=True)
        L.seed_everything(42)
        train_set, val_set = torch.utils.data.random_split(train_dataset, [45000, 5000])

        # Loading the test set
        test_set = CIFAR10(root=DATASET_PATH, train=False, transform=transform, download=True)

        # We define a set of data loaders that we can use for various purposes later.
        train_loader = data.DataLoader(train_set, batch_size=256, shuffle=True, drop_last=True, pin_memory=True, num_workers=4)
        val_loader = data.DataLoader(val_set, batch_size=256, shuffle=False, drop_last=False, num_workers=4)
        test_loader = data.DataLoader(test_set, batch_size=256, shuffle=False, drop_last=False, num_workers=4)


        def get_train_images(num):
            return torch.stack([train_dataset[i][0] for i in range(num)], dim=0)


        for id, frame in img_seq:
            # Apply transform
            w, h = frame.resolution()
            frame = self.transform({'image': frame.get()[...,0:3]})['image']
            frame = torch.from_numpy(frame).unsqueeze(0).to(self.device)
            
        
        # Start training
        trainer = L.Trainer(
            accelerator="auto",
            devices=1,
            max_epochs=30,
            callbacks=[
                #ModelCheckpoint(save_weights_only=True),
                #GenerateCallback(get_train_images(8), every_n_epochs=10),
                #LearningRateMonitor("epoch"),
            ],
        )
        trainer.logger._default_hp_metric = None  # Optional logging argument that we don't need
        trainer.fit(model, train_loader, val_loader)
        # Test best model on validation and test set
        val_result = trainer.test(model, dataloaders=val_loader, verbose=False)
        test_result = trainer.test(model, dataloaders=test_loader, verbose=False)
        result = {"test": test_result, "val": val_result}


        # Store data in image sequence and metadata
        #self.sequence.append(ImgBuffer(img=depth), id)
        
        ## Run model
        #with torch.no_grad():
        #    depth = self.model(frame)

        
    def get(self) -> Sequence:
        return self.sequence
        

class RtiEncoder(nn.Module):
    def __init__(self, input_channels, base_channel_size, latent_dim, act_fn: object):
        super().__init__()
        self.net = nn.Sequential(
            nn.Linear(input_channels, input_channels),
            act_fn(),
            nn.Linear(input_channels, input_channels),
            act_fn(),
            nn.Linear(input_channels, input_channels),
            act_fn(),
            nn.Linear(input_channels, latent_dim),
            act_fn()
        )
    
    def forward(self, lights_rgb):
        return self.net(lights_rgb)
    
class RtiDecoder(nn.Module):
    def __init__(self, input_channels, base_channel_size, latent_dim, act_fn: object):
        super().__init__()
        self.linear = nn.Sequential(nn.Linear(latent_dim + 2, input_channels), act_fn())
        self.net = nn.Sequential(
            nn.Linear(input_channels, input_channels),
            act_fn(),
            nn.Linear(input_channels, input_channels),
            act_fn(),
            nn.Linear(input_channels, input_channels),
            act_fn(),
            nn.Linear(input_channels, 3),
        )
    
    def forward(self, x, light_direction):
        x = self.linear(torch.concat((x, light_direction), -1)) # TODO -1?
        x = x.reshape(x.shape[0], -1, 4, 4) # TODO
        x = self.net(x)
        return x

class RtiAutoencoder(L.LightningModule):
    def __init__(
        self,
        light_count: int,
        latent_dim: int = 9,
        encoder_class: object = RtiEncoder,
        decoder_class: object = RtiDecoder,
        act_fn: object = nn.ELU,
        width: int = 1920,
        height: int = 1080,
    ):
        super().__init__()
        # Saving hyperparameters of autoencoder
        self.save_hyperparameters()
        # Creating encoder and decoder
        self.encoder = encoder_class(light_count*3, latent_dim, act_fn)
        self.decoder = decoder_class(light_count*3, latent_dim, act_fn)
        # Example input array needed for visualizing the graph of the network
        #self.example_input_array = torch.zeros(2, light_count*3, width, height)

    def forward(self, lights_rgb, light_direction):
        """The forward function takes in an image and returns the reconstructed image."""
        z = self.encoder(lights_rgb)
        x_hat = self.decoder(torch.concat((z, light_direction)))
        return x_hat

    def _get_reconstruction_loss(self, batch):
        """Given a batch of images, this function returns the reconstruction loss (MSE in our case)."""
        x, _ = batch  # We do not need the labels
        x_hat = self.forward(x)
        loss = F.mse_loss(x, x_hat, reduction="none")
        loss = loss.sum(dim=[1, 2, 3]).mean(dim=[0])
        return loss

    def configure_optimizers(self):
        optimizer = optim.Adam(self.parameters(), lr=1e-3)
        # Using a scheduler is optional but can be helpful.
        # The scheduler reduces the LR if the validation performance hasn't improved for the last N epochs
        scheduler = optim.lr_scheduler.ReduceLROnPlateau(optimizer, mode="min", factor=0.2, patience=20, min_lr=5e-5)
        return {"optimizer": optimizer, "lr_scheduler": scheduler, "monitor": "val_loss"}

    def training_step(self, batch, batch_idx):
        loss = self._get_reconstruction_loss(batch)
        self.log("train_loss", loss)
        return loss

    def validation_step(self, batch, batch_idx):
        loss = self._get_reconstruction_loss(batch)
        self.log("val_loss", loss)

    def test_step(self, batch, batch_idx):
        loss = self._get_reconstruction_loss(batch)
        self.log("test_loss", loss)
