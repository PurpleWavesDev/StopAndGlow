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
        self._result = Sequence()
        self._mode = ''
    
    def getDefaultSettings() -> dict:
        return {'mode': 'alpha'}
    
    def process(self, seq: Sequence, calibration: Calibration, settings={}):
        self._result = Sequence()
        
        # Settings
        self._mode = GetSetting(settings, 'mode', 'alpha')
        threshold = GetSetting(settings, 'threshold', 20)
        exposure = GetSetting(settings, 'exposure', 80)
        
        self._view_idx = 0
        
        # Execute command for mode
        log.info(f"Stacking lights with mode {self._mode}")
        match self._mode:
            case 'alpha':
                # Get average image of all lamps with position parallel to the image plane
                # TODO: Two images with only left and right lamps on, then merge sides -> hoping to get reflections in the background only on the "wrong" side
                buf_r = self.avgLights(seq, calibration, lambda lightpos: lightpos.getXYZ()[1] <= 0.6 and lightpos.getXYZ()[1] > -0.6 and lightpos.getXYZ()[0] > 0.0)
                buf_r.set(buf_r.get()*exposure)
                buf_l = self.avgLights(seq, calibration, lambda lightpos: lightpos.getXYZ()[1] <= 0.6 and lightpos.getXYZ()[1] > -0.6 and lightpos.getXYZ()[0] < 0.0)
                buf_l.set(buf_l.get()*exposure)
                
                #imgutils.SaveEval(buf.get(), 'alpha_lights')
                # Binary Filter
                threshold1 = cv.threshold(buf_r.asDomain(ImgDomain.sRGB).asInt().get(), threshold, 255, cv.THRESH_BINARY)[1] # + cv.THRESH_OTSU
                threshold2 = cv.threshold(buf_l.asDomain(ImgDomain.sRGB).asInt().get(), threshold, 255, cv.THRESH_BINARY)[1] # + cv.THRESH_OTSU
                
                self._result.append(ImgBuffer(img=threshold1), 0)
                self._result.append(ImgBuffer(img=threshold2), 1)
                self._result.append(buf_r, 2)
                self._result.append(buf_l, 3)
            
            case 'hdri':
                # Sums up all lights with value from blurred HDRI
                pass
            
            case 'average':
                # Takes average of all images
                self._result.append(self.avgLights(seq, calibration, lambda lightpos: True), 0)
            
            # TODO: Reflectance only for front facing lights? (but avg for all)
            case 'reflectance':
                # Takes average of all images
                avg = self.avgLights(seq, calibration, lambda lightpos: True)
                # Set minimum value to make division stable
                avg.set(np.maximum(avg.get(), np.full(avg.get().shape, 0.0005))) # TODO: What is a good value?
                for id, img in seq:
                    self._result.append(ImgBuffer(path=img.getPath(), img=img.get()/avg.get(), domain=ImgDomain.Lin), id)
            
            case _:
                log.error(f"Unknown mode '{self._mode}'")
                
        
    def avgLights(self, seq, cal, func) -> ImgBuffer:
        count = 0
        img = ImgBuffer.CreateEmpty(seq.get(0).resolution()).get()
        for id, lightpos in cal:
            if func(lightpos):
                if id in seq.getKeys():
                    img += seq[id].asDomain(ImgDomain.Lin).get()
                    count += 1
        if count > 0:
            img /= (count)
        
        return ImgBuffer(img=img, domain=ImgDomain.Lin)
        
    def get(self) -> Sequence:
        # Metadata
        self._result.setMeta('lightstack_mode', self._mode)
        return self._result
    

