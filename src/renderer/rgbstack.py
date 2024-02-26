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
#import src.renderer.ti_stack as tstack


class RgbStacker(Renderer):
    name = "RGB Stacker"

    def __init__(self):
        self._stacked = ImgBuffer()
        self._domain = ImgDomain.Keep
            
    # Loading, processing etc.
    def load(self, rti_seq: Sequence):
        # Copy frame
        if len(rti_seq) == 1:
            self._stacked = rti_seq.get(0)
            self._domain = self._stacked.domain()
    
    def get(self) -> Sequence:
        seq = Sequence()
        seq.append(self._stacked, 0)
        # Metadata
        #seq.setMeta('key', val)
        return seq
    
    def process(self, img_seq: Sequence, config: Config, settings={'domain': ImgDomain.Keep}):
        # Get channels and stack them
        self._domain = settings['domain'] if 'domain' in settings else ImgDomain.Keep
        r = img_seq[0].asDomain(self._domain).r()
        g = img_seq[0].asDomain(self._domain).g()
        b = img_seq[0].asDomain(self._domain).b()
        
        # Stacking
        self._stacked = ImgOp.StackChannels([r, g, b])        
    
    # Render settings
    def getRenderModes(self) -> list:
        return ("Stacked")
    
    def getRenderSettings(self, render_mode) -> RenderSettings:
        return RenderSettings(is_linear=self._domain == ImgDomain.Lin, with_exposure=True)
    
    def render(self, render_mode, buffer, hdri=None):
        # Return stacked image
        y, x = buffer.shape
        buffer.from_numpy(self._stacked.get()[0:y, 0:x, :]) # TODO: Proper rescaling
        