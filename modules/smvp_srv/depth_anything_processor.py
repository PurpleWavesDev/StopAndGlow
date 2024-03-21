import numpy as np
import cv2 as cv

import torch
import torch.nn.functional as F
from torchvision.transforms import Compose
from depth_anything.dpt import DepthAnything
from depth_anything.util.transform import Resize, NormalizeImage, PrepareForNet

#
# 'depth_anything_model', 'vitl', ['vits', 'vitb', 'vitl']


class DAProcessor():
    """Wrapper of the Depth-Anything framework"""
    def __init__(self, flagdict):
        # Check if a specific model was requested, use large as default
        Com.info("Initializing Depth Anything..")

        self.device = torch.device("cuda") if torch.cuda.is_available() else torch.device("cpu")
        self.model = DepthAnything.from_pretrained('LiheYoung/depth_anything_{}14'.format(flagdict['depth_anything_model'])).to(self.device).eval()
        
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
            Com.info("CUDA acceleration for MiDaS enabled.")

    def process_frame(self, frame: np.ndarray, bounds: "tuple[list, list]", original: np.ndarray, bounds_original: "tuple[list, list]") -> np.ndarray:
        # Apply transform
        h, w = frame.shape[:2]
        frame = self.transform({'image': frame})['image']
        frame = torch.from_numpy(frame).unsqueeze(0).to(self.device)
        
        # Run model
        with torch.no_grad():
            depth = self.model(frame)
        
        # Scale back and normalize
        depth = F.interpolate(depth[None], (h, w), mode='bilinear', align_corners=False)[0, 0]
        depth = (depth - depth.min()) / (depth.max() - depth.min())
        depth = depth.cpu().numpy()
        depth = np.repeat(depth[..., np.newaxis], 3, axis=-1)

        return depth
