import logging as log

import numpy as np
from numpy.typing import ArrayLike
import math
import cv2 as cv

import taichi as ti
import taichi.math as tm
import taichi.types as tt

from .renderer import *

from ..data import *
from ..utils import ti_base as tib


class RgbStacker(Renderer):
    name = "RGB Stacker"

    def __init__(self):
        self._stacked = ImgBuffer()
        self._domain = ImgDomain.Keep
        self._rescaled = None
            
    # Loading, processing etc.
    def load(self, sequence: Sequence):
        # Copy frame
        if len(sequence) == 1:
            self._stacked = sequence.get(0)
            self._domain = self._stacked.domain()
            self._rescaled = None
    
    def get(self) -> Sequence:
        seq = Sequence()
        seq.append(self._stacked, 0)
        # Metadata
        #seq.setMeta('key', val)
        return seq
    
    def process(self, img_seq: Sequence, calibration: Calibration, settings={'domain': ImgDomain.Keep}):
        # Get channels and stack them
        self._domain = settings['domain'] if 'domain' in settings else ImgDomain.Keep
        r = img_seq[0].asDomain(self._domain).r()
        g = img_seq[1].asDomain(self._domain).g()
        b = img_seq[2].asDomain(self._domain).b()
        
        # Stacking
        self._stacked = imgutils.StackChannels([r, g, b])
        self._rescaled = None
    
    # Render settings
    def getRenderModes(self) -> list:
        return ("Stacked")
    
    def getRenderSettings(self, render_mode) -> RenderSettings:
        return RenderSettings(is_linear=self._domain == ImgDomain.Lin, with_exposure=True)
    
    def render(self, render_mode, buffer, hdri=None):
        # Return stacked image
        if self._rescaled is None:
            y, x = buffer.shape
            factor = x / self._stacked.resolution()[0]
            self._rescaled = self._stacked.scale(factor).crop((x, y)).get()
        buffer.from_numpy(self._rescaled)
        