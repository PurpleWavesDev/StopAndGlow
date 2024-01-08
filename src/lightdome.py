import logging as log
import numpy as np
import math

import cv2 as cv

from src.imgdata import *
from src.config import *


class Lightdome:
    def __init__(self, config: Config = None):
        self.img_res_base = 1000
        self.img_background = 10
        self.blur_size = 15
        self._lightVals = dict()
        if config is not None:
            self.setConfig(config)
        
    def setConfig(self, config: Config):
        self._config = config
        self._lightVals.clear()
    
    def sampleHdri(self, hdri: ImgBuffer):
        res_y, res_x = hdri.get().shape[:2]
        blur_size = int(self.blur_size*res_y/100)
        blur_size += 1-blur_size%2 # Make it odd
                        
        # Blur HDRI to reduce errors
        # TODO: Conversion lin->srgb->blur->lin reduces extremes but they are probably necessary for accurate light energy?
        #hdri = hdri.asDomain(ImgDomain.sRGB)
        hdri = ImgBuffer(img=cv.GaussianBlur(hdri.get(), (blur_size, blur_size), -1))
        #hdri = hdri.asDomain(ImgDomain.Lin) # Conversion back
        
        for light in self._config:
            # Sample point in HDRI
            latlong = light['latlong']
            x = int(round(res_x * latlong[1]/360.0))
            y = int(round(res_y/2 - res_y * latlong[0]/180.0))
            self._lightVals[light['id']] = hdri[x, y]
    
    def sampleUV(self, f):
        for light in self._config:
            sample = f(light['uv'])
            self._lightVals[light['id']] = sample
    
    def sampleLatLong(self, f):
        for light in self._config:
            sample = f(light['latlong'])
            self._lightVals[light['id']] = sample

    def getLights(self, domain=ImgDomain.Lin, type='uint8'):
        return self._lightVals

    
    def generateUV(self, image=None):
        # Generate RGB image and draw blue circle for sphere
        res = self.img_res_base
        if image is None:
            image = ImgBuffer(img=np.full((res, res, 3), self.img_background, dtype='uint8'), domain=ImgDomain.sRGB)
        else:
            image = image.asDomain(ImgDomain.sRGB).asInt()
            res = min(image.get().shape[:2])
        res_2 = int(round(res/2))
        
        # Draw sphere contour
        cv.circle(image.get(), (res_2, res_2), res_2, (0, 0, 255), 2)
        light_radius = 6 # TODO: Calculate
        
        for light_entry in self._config:
            value = self._lightVals[light_entry['id']].asDomain(ImgDomain.sRGB).asInt().get()[0][0].tolist() if not None else (0)
            x = int(round(res_2 + res_2*light_entry['uv'][0]))
            y = int(round(res_2 - res_2*light_entry['uv'][1]))
            # Fill
            cv.circle(image.get(), (x, y), light_radius, value, cv.FILLED)
            # Outline
            cv.circle(image.get(), (x, y), light_radius, (255, 255, 255), 1)
            
        return image
        
    def generateLatLong(self, image=None):
        # Generate RGB image with aspect ratio 2:1
        res_x, res_y = (self.img_res_base * 2, self.img_res_base)
        if image is None:
            image = ImgBuffer(img=np.full((res_x, res_y, 3), self.img_background, dtype='uint8'), domain=ImgDomain.sRGB)
        else:
            image = image.asDomain(ImgDomain.sRGB).asInt()
            res_y, res_x = image.get().shape[:2]
        light_radius = 6 # TODO: Calculate
        
        # Draw lights as circles with fill
        for light_entry in self._config:
            value = self._lightVals[light_entry['id']].asDomain(ImgDomain.sRGB).asInt().get()[0][0].tolist() if not None else (0)
            x = int(round(res_x * light_entry['latlong'][1] / 360))
            y = int(round(res_y/2 - (res_y/2) * light_entry['latlong'][0] / 90))
            # Fill
            cv.circle(image.get(), (x, y), light_radius, value, cv.FILLED)
            # Outline
            cv.circle(image.get(), (x, y), light_radius, (255, 255, 255), 1)

        return image

        