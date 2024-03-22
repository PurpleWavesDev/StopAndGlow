import numpy as np
from numpy.typing import ArrayLike
import cv2 as cv
import logging as log
from enum import StrEnum

import torch
import torch.nn.functional as F
from torchvision.transforms import Compose

from .depth_anything.dpt import DepthAnything
from .depth_anything.util.transform import Resize, NormalizeImage, PrepareForNet
from .renderer import *

from ..data import *
from ..utils import ti_base as tib


class DepthAnythingModels(StrEnum):
    large = 'vitl'
    base = 'vitb'
    small = 'vits'

class DepthEstimator(Renderer):
    """Wrapper of the Depth-Anything framework"""
    name = "Depth Estimator"
    name_short = "depth"
    
    def getDefaultSettings() -> dict:
        return {'model': DepthAnythingModels.large}
    
    def process(self, img_seq: Sequence, calibration: Calibration, settings: dict):
        # Check if a specific model was requested, use large as default
        log.debug("Initializing Depth Anything")

        self.device = torch.device("cuda") if torch.cuda.is_available() else torch.device("cpu")
        self.model = DepthAnything.from_pretrained('LiheYoung/depth_anything_{}14'.format(settings['model'])).to(self.device).eval()
        
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
        
        # Print if CUDA is available
        if self.device.type == 'cuda':
            log.debug("CUDA acceleration for MiDaS enabled")
        
        self.setSequence(img_seq)
    
    def setSequence(self, img_seq: Sequence):
        self._sequence = img_seq

    # Render settings
    def getRenderModes(self) -> list:
        return ['depth']
    def getRenderSettings(self, render_mode) -> RenderSettings:
        return RenderSettings(is_linear=True, with_exposure=True)    

    # Rendering
    def render(self, render_mode, buffer, hdri=None):
        #buffer.from_torch(self.getDepthTorch(self._sequence.getPreview())) # TODO: Gray scale image to RGB
        buffer.from_numpy(self.getDepth(self._sequence.getPreview()))
        
    def getDepth(self, frame: ImgBuffer) -> ArrayLike:
        depth = self.getDepthTorch(frame).cpu().numpy()
        depth = np.repeat(depth[..., np.newaxis], 3, axis=-1)
        return depth
    
    def getDepthTorch(self, frame: ImgBuffer):
        # Apply transform
        w, h = frame.resolution()
        frame = self.transform({'image': frame.get()})['image']
        frame = torch.from_numpy(frame).unsqueeze(0).to(self.device)
        
        # Run model
        with torch.no_grad():
            depth = self.model(frame)
        
        # Scale back and normalize
        depth = F.interpolate(depth[None], (h, w), mode='bilinear', align_corners=False)[0, 0]
        depth = (depth - depth.min()) / (depth.max() - depth.min())
        
    