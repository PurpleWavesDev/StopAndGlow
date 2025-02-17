import logging as log

import numpy as np
from numpy.typing import ArrayLike
import math
import cv2 as cv

import taichi as ti
import taichi.math as tm
import taichi.types as tt

from .processor import *
from ..data import *
from ..utils import ti_base as tib


class ExpoBlender(Processor):
    name = "expoblend"
    
    def __init__(self):
        self._blended = Sequence()
    
    def getDefaultSettings() -> dict:
        return {'blend_threshold': 0.1, 'blend_factor': 2.0}
    
    def process(self, seq_list: list[Sequence], calibration: Calibration, settings={}):
        if type(seq_list) != list or len(seq_list) <= 1:
            log.error("Must provide at least two sequences for stacking")
            return
        
        # Settings
        exposure_times = np.array(settings['exposure'] if 'exposure' in settings else [], dtype='float32')
        if len(exposure_times) < len(seq_list):
            log.error(f"Must provide exposure time list with 'exposure' key in settings dict with same length as sequence list ({len(seq_list)})")
            return
        
        blend_threshold = GetSetting(settings, 'blend_threshold', 0.1)
        blend_factor = GetSetting(settings, 'blend_factor', 2.0)
        
        self._view_idx = 0
        self._blended = Sequence()
        self._blended._meta = seq_list[0]._meta.copy()
        self._blended.setDirectory(seq_list[0].directory())
        self._blended.setName(seq_list[0].name())
        
        # Prepare Taichi buffer
        res_x, res_y = seq_list[0].get(0).resolution()
        buffer = ti.ndarray(tib.pixvec, (len(seq_list), res_y, res_x))
        
        # Merge each frame
        for id, _ in seq_list[0]:
            # Stack images to prepare input buffer
            buffer.from_numpy(np.stack([seq[id].asDomain(ImgDomain.Lin).get() for seq in seq_list], dtype='float32'))
            # Blend and append
            exposure_blending(buffer, exposure_times, blend_threshold, blend_factor)
            self._blended.append(ImgBuffer(img=buffer.to_numpy()[0, :], domain=ImgDomain.Lin), id)
        # Don't forget mask frame
        buffer.from_numpy(np.stack([seq.getPreview().asDomain(ImgDomain.Lin).get() for seq in seq_list], dtype='float32'))
        exposure_blending(buffer, exposure_times, blend_threshold, blend_factor)
        self._blended.setPreview(ImgBuffer(img=buffer.to_numpy()[0, :], domain=ImgDomain.Lin))
        
        
    def get(self) -> Sequence:
        # Metadata
        #seq.setMeta('key', val)
        return self._blended
    

@ti.kernel
def exposure_blending(images: tt.ndarray(tib.pixvec, 3), exposure_values: tt.ndarray(ti.f32, 1), blend_threshold: ti.f32, blend_factor: ti.f32):
    # Iterate over pixels
    for y, x in ti.ndrange(images.shape[1], images.shape[2]):
        # Iterate over pairs of images
        for n in range(1, images.shape[0]):
            # blend images[n] to images[0] with exposure of darkest frame (last frame)
            #if exposure_values[0] > exposure_values[n]:
            
            # Next frame was darker, adjust exposure of first image
            images[0, y, x] *= exposure_values[n] / exposure_values[0]
            # Alpha is brightest parts of next image -> parts that have more information than merged frame
            alpha = tm.clamp((images[n, y, x]-blend_threshold) * blend_factor, 0.0, 1.0)
            # Take values from new frame where alpha is high
            images[0, y, x] = images[0, y, x] * (1-alpha) + images[n, y, x] * alpha
            
            ## Code to visualize mask
            #if n == 1:
            #    val = images[0, y, x][0] * exposure_values[0] / exposure_values[2] # Make R channel as bright as 3. exposure
            #    images[0, y, x] = [val * (1.0-alpha[0]), val * alpha[0], 0.0]
            #elif n == 2:
            #    images[0, y, x] = [images[0, y, x][0] * (1.0-alpha[0]), images[0, y, x][1] * (1.0-alpha[0]), alpha[0]]

