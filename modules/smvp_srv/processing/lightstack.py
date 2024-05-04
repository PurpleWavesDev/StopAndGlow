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


class LightstackProcessor(Processor):
    name = "lightstack"
    
    def __init__(self):
        self._result = ImgBuffer()
        self._mode = ''
    
    def getDefaultSettings() -> dict:
        return {'mode': 'alpha'}
    
    def process(self, seq: Sequence, calibration: Calibration, settings={}):
        # Settings
        self._mode = GetSetting(settings, 'mode', 'alpha')
        threshold = GetSetting(settings, 'threshold', 30)
        exposure = GetSetting(settings, 'exposure', 50)
        
        self._view_idx = 0
                
        # Execute command for mode
        match self._mode:
            case 'alpha':
                # Get average image of all lamps with position parallel to the image plane
                buf = self.avgLights(seq, calibration, lambda lightpos: lightpos.getXYZ()[1] <= 0.5 and lightpos.getXYZ()[1] > 0.1)
                buf.set(buf.get()*exposure)
                imgutils.SaveEval(buf.get(), 'alpha_lights')
                # Binary Filter
                threshold = cv.threshold(buf.asDomain(ImgDomain.sRGB).asInt().get(), threshold, 255, cv.THRESH_BINARY)[1] # + cv.THRESH_OTSU

        self._result = ImgBuffer(img=threshold)

        
    def avgLights(self, seq, cal, func):
        count = 0
        img = ImgBuffer.CreateEmpty(seq.get(0).resolution()).get()
        for id, lightpos in cal.getLights().items():
            if func(lightpos):
                if id in seq.getKeys():
                    img += seq[id].asDomain(ImgDomain.Lin).get()
                    count += 1
        if count > 0:
            img /= (count)
        
        return ImgBuffer(img=img, domain=ImgDomain.Lin)
        
    def get(self) -> Sequence:
        # Metadata
        seq = Sequence()
        seq.setMeta('lightstack_mode', self._mode)
        seq.append(self._result, 0)
        
        return seq
    

