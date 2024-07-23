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
        num_lights = 50 #len(img_seq)
        model = RtiAutoencoder(num_lights)
        with utils.logging_disabled():
            L.seed_everything(42)

        # Loading the training dataset. We need to split it into a training and validation part
        log.debug("Loading data")
        dataset = self.prepareData(img_seq, calibration)
        log.debug("Splitting data")
        train_set, val_set = self.splitData(dataset)

        # We define a set of data loaders that we can use for various purposes later.
        train_loader = torch.utils.data.DataLoader(train_set, batch_size=256, shuffle=True, drop_last=True, pin_memory=True, num_workers=4)
        val_loader = torch.utils.data.DataLoader(val_set, batch_size=256, shuffle=False, drop_last=False, num_workers=4)
        
        # Start training
        log.debug("Starting training")
        trainer = L.Trainer(
            accelerator="auto",
            devices=1,
            max_epochs=30,
            callbacks=[
                #ModelCheckpoint(save_weights_only=True),
                #GenerateCallback(self.getImages(dataset, 8), every_n_epochs=10),
                #LearningRateMonitor("epoch"),
            ],
        )
        trainer.logger._default_hp_metric = None  # Optional logging argument that we don't need
        trainer.fit(model, train_loader, val_loader)
        # Test best model on validation set
        val_result = trainer.test(model, dataloaders=val_loader, verbose=False)
        log.info(f"Validation result {val_result}")

        # Store data in image sequence and metadata
        #self.sequence.append(ImgBuffer(img=depth), id)
        
        ## Run model
        #with torch.no_grad():
        #    depth = self.model(frame)

        
    def get(self) -> Sequence:
        return self.sequence
    
    
    ## Data methods
    def prepareData(self, img_seq: Sequence, calibration: Calibration):
        num_lights = 50 #len(img_seq)
        res_x, res_y = img_seq.get(0).resolution()
        datalen = num_lights * res_y*res_x

        # Read all images into single buffer        
        #allimgdata = np.zeros((num_lights, res_y*res_x * 3),np.float32)
        #for i, id in enumerate(img_seq.getKeys()):
        #    img = img_seq[id].asDomain(ImgDomain.Lin).get(trunk_alpha=True)
        #    allimgdata[i, :] = np.ravel(img)
        
        ## Build input and target tensors
        # TODO: Unable to allocate 1.59 TiB for an array with shape (549504000, 795) and data type float32 WTF
        #inputdata  = np.zeros((datalen, num_lights * 3), np.float32) # Pixel and direction data for encoder
        lightdata  = np.zeros((datalen, 2), np.float32)  # Directions for all lights for decoder
        targetdata = np.zeros((datalen, 3), np.float32)  # RGB pixel values of all lights
        
        for i, id in enumerate(img_seq.getKeys()):
            if i >= 50:
                break
            
            # Fill target data
            target_tmp = img_seq[id].asDomain(ImgDomain.Lin).get(trunk_alpha=True)
            #target_tmp = np.reshape(allimgdata[i], (res_y*res_x, 3))
            target_tmp = np.reshape(target_tmp, (res_y*res_x, 3))
            targetdata[(res_y*res_x * i):(res_y*res_x * (i+1)),:] = target_tmp
            
            # Fill input data
            #input_tmp = np.reshape(allimgdata, (num_lights, res_y*res_x, 3))
            #input_tmp = np.transpose(input_tmp, (1, 0, 2))
            #input_tmp = np.reshape(input_tmp, (res_y*res_x, num_lights * 3))
            #inputdata[(res_y*res_x * i):(res_y*res_x*(i+1)), :] = input_tmp
            
            # Fill light data
            ld = np.transpose(calibration[id].getZVecNorm())
            lt = np.tile(ld, (res_y*res_x, 1))
            lt = np.reshape(lt, (res_y*res_x, 2))
            lightdata[(res_y*res_x * i):(res_y*res_x*(i+1)),:] = lt
            
            # Delete temp vars to free up memory
            del target_tmp, ld, lt # input_tmp
                    
        # Converting numpy array to Tensor
        #inputdata  = torch.from_numpy(intputdata).float()
        lightdata  = torch.from_numpy(lightdata).float()
        targetdata = torch.from_numpy(targetdata).float()
        
        ## Transformations applied to input image data
        transform = transforms.Compose([transforms.Normalize((0.5,), (0.5,))])
        #input_transformed = transform(intputdata) # transform(torch.from_numpy(intputdata).float())
        #inputdata = torch.stack([transform(targetdata), lightdata]) # tensor size ..., C, H, W expected

        
        return torch.utils.data.TensorDataset(lightdata, targetdata) # TODO single dataset? what order of tensors?

    def splitData(self, datasets):
        # Split and return
        train_set, val_set = torch.utils.data.random_split(datasets, [0.9, 0.1])
        return train_set, val_set
    
    def getImages(self, dataset, num):
        return torch.stack([dataset[i][0] for i in range(num)], dim=0)

        

class RtiEncoder(nn.Module):
    def __init__(self, input_channels, latent_dim, act_fn: object):
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
    def __init__(self, input_channels, latent_dim, act_fn: object):
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
        x, y = batch  # We do not need the labels
        x_hat = self.forward(y, x)
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
