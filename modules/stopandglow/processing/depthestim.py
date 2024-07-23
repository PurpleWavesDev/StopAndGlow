import numpy as np
from numpy.typing import ArrayLike
import cv2 as cv
import logging as log
from enum import StrEnum

import torch
import torch.nn.functional as F
from torchvision.transforms import Compose

from .processor import *
from .depth_anything.dpt import DepthAnything
from .depth_anything.util.transform import Resize, NormalizeImage, PrepareForNet

from ..data import *
from ..utils import ti_base as tib
from ..utils.utils import logging_disabled


class DepthAnythingModels(StrEnum):
    large = 'vitl'
    base = 'vitb'
    small = 'vits'

class DepthEstimator(Processor):
    """Wrapper of the Depth-Anything framework"""
    name = "depthestim"
    
    def __init__(self):
        self.device = torch.device("cuda") if torch.cuda.is_available() else torch.device("cpu")
        if self.device.type == 'cuda':
            log.debug("CUDA acceleration for MiDaS enabled")

        self.transform = Compose([
            Resize(
                width=518,
                height=518,
                resize_target=False,
                keep_aspect_ratio=True,
                ensure_multiple_of=14,
                resize_method='lower_bound',
                image_interpolation_method=cv.INTER_CUBIC,
            ),
            NormalizeImage(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
            PrepareForNet(),
        ])
        
        self.model = None
        self.model_type = ""
        self.sequence = Sequence()
        

    def getDefaultSettings() -> dict:
        return {'model': DepthAnythingModels.large, 'rgb': True}
    
    def process(self, img_seq: Sequence, calibration: Calibration, settings: dict):
        self.sequence = Sequence()
        
        # Load model if not loaded already
        new_model_type = GetSetting(settings, 'model', DepthAnythingModels.large)
        if self.model is None or self.model_type != new_model_type:
            self.model_type = new_model_type
            with logging_disabled():
                self.model = DepthAnything.from_pretrained(f'LiheYoung/depth_anything_{self.model_type}14').to(self.device).eval()
        
        for id, frame in img_seq:
            # Apply transform
            w, h = frame.resolution()
            frame = self.transform({'image': frame.get()[...,0:3]})['image']
            frame = torch.from_numpy(frame).unsqueeze(0).to(self.device)
            
            # Run model
            with torch.no_grad():
                depth = self.model(frame)
            
            # Scale back and normalize
            depth = F.interpolate(depth[None], (h, w), mode='bilinear', align_corners=False)[0, 0]
            depth = (depth - depth.min()) / (depth.max() - depth.min())
            # To numpy, add other channels
            depth = depth.cpu().numpy()
            if GetSetting(settings, 'rgb', True, dtype=bool):
                depth = np.repeat(depth[..., np.newaxis], 3, axis=-1)
            else:
                depth = np.repeat(depth[..., np.newaxis], 1, axis=-1)
            
            # Add to sequence
            self.sequence.append(ImgBuffer(img=depth), id)
        
    def get(self) -> Sequence:
        return self.sequence
        
    