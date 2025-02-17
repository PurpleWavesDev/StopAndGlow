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


class RgbStacker(Processor):
    name = "rgbstack"

    def __init__(self):
        self._stacked = ImgBuffer()
        self._domain = ImgDomain.Keep
        self._rescaled = None
    
    def getDefaultSettings() -> dict:
        return {'domain': ImgDomain.Keep}
    
    def process(self, img_seq: Sequence, calibration: Calibration, settings={}):
        # Get channels and stack them
        self._domain = GetSetting(settings, 'domain', ImgDomain.Keep)
        r = img_seq[0].asDomain(self._domain).r()
        g = img_seq[1].asDomain(self._domain).g()
        b = img_seq[2].asDomain(self._domain).b()
        
        # Stacking
        self._stacked = imgutils.StackChannels([r, g, b])

    def get(self) -> Sequence:
        seq = Sequence()
        seq.append(self._stacked, 0)
        # Metadata
        #seq.setMeta('key', val)
        return seq
    