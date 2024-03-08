import logging as log

import numpy as np
from numpy.typing import ArrayLike
import math
import cv2 as cv

import taichi as ti
import taichi.math as tm
import taichi.types as tt

from src.imgdata import *
from src.sequence import *
from src.config import *

from src.renderer.renderer import *
import src.ti_base as tib


class ExpoBlender(Renderer):
    name = "Exposure Blender"

    def __init__(self):
        self._blended = Sequence()
        self._rescaled = None
        self._view_idx = 0
            
    # Loading, processing etc.
    def load(self, sequence: Sequence):
        # Save sequence
        self._blended = sequence
    
    def get(self) -> Sequence:
        # Metadata
        #seq.setMeta('key', val)
        return self._blended
    
    def process(self, seq_list: list[Sequence], config: Config, settings={}):
        if type(seq_list) != list or len(seq_list) <= 1:
            log.error("Must provide at least two sequences for stacking, aborting.")
            return
        # Settings
        exposure_times = np.array(settings['exposure'] if 'exposure' in settings else list())
        if len(exposure_times) != len(seq_list):
            log.error(f"Must provide exposure time list with 'exposure' key in settings dict with same length as sequence list ({len(seq_list)}), aborting.")
            return
        blend_threshold = 0.3
        blend_factor = 3.0
        self._view_idx = 0
        
        # Prepare Taichi buffer
        res_x, res_y = seq_list[0].get(0).resolution()
        buffer = ti.ndarray(tib.pixvec, (len(seq_list), rex_y, res_x))
        
        # Merge each frame
        for i in range(len(seq_list[0])):
            # Stack images to prepare input buffer
            buffer_in.from_numpy(np.stack([seq.get(i).asDomain(ImgDomain.Lin).get() for seq in seq_list]))
            # Blend
            exposure_blending(buffer_in, exposure_times, blend_threshold, blend_factor)
    
    # Render settings
    def getRenderModes(self) -> list:
        return ("Blended")
    
    def getRenderSettings(self, render_mode) -> RenderSettings:
        return RenderSettings(is_linear=True, with_exposure=True, req_keypress_events=True)
    
    def keypressEvent(self, event_key):
            if event_key in ['a']: # Left
                self._view_idx = (len(self._sequence)+self._view_idx-1) % len(self._sequence)
                self._rescaled = None
            elif event_key in ['d']: # Right
                self._view_idx = (self._view_idx+1) % len(self._sequence)
                self._rescaled = None
    
    def render(self, render_mode, buffer, hdri=None):
        # Return stacked image
        if self._rescaled is None:
            y, x = buffer.shape
            factor = x / self._blended.get(self._view_idx).resolution()[0]
            self._rescaled = self._blended.get(self._view_idx).scale(factor).crop((x, y)).get()
        buffer.from_numpy(self._rescaled)

@ti.kernel
def exposure_blending(images: tt.ndarray(tib.pixvec, 3), exposure_values: tt.ndarray(ti.f32, 1), blend_threshold: ti.f32, blend_factor: ti.f32):
    # Iterate over pixels
    for y, x in ti.ndrange(images.shape[1], images.shape[2]):
        # Iterate over pairs of images
        for n in range(1, images.shape[0]):
            # blend images[n] to images[0]
            # Adjust exposure of new image
            images[n] *= exposure_values[0] / exposure_values[n]
            # Get alpha mask from brightness values of brighter image 
            if exposure_values[0] > exposure_values[n]:
                alpha = tm.clamp((exposure_values[0]-blend_threshold) * blend_factor, 0, 1)
                images[0] = images[0] * (1-alpha) + images[n] * alpha 
            else:
                alpha = tm.clamp((exposure_values[1]-blend_threshold) * blend_factor, 0, 1)
                images[0] = images[0] * alpha + images[n] * (1-alpha) 
