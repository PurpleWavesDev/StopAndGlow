import logging as log
import random
import numpy as np
import math

import cv2 as cv

from src.imgdata import *
from src.sequence import Sequence
from src.config import *
from src.lights import *

DMX_MAX_VALUE = 255


class Lightdome:
    def __init__(self, hw = None):
        self.img_res_base = 1000
        self.img_background = 10
        self.blur_size = 15
        self._lightVals = dict()
        if hw is not None:
            self.setHw(hw)
    
    def setHw(self, hw):
        self._config = hw.config
        self._lights = hw.lights
        self._lightVals.clear()
    
    def processHdri(self, hdri: ImgBuffer, exposure_correction=1):
        res_y, res_x = hdri.get().shape[:2]
        blur_size = int(self.blur_size*res_y/100)
        blur_size += 1-blur_size%2 # Make it odd
        
        # Blur HDRI to reduce errors
        # TODO: Conversion lin->srgb->blur->lin reduces extremes but they are probably necessary for accurate light energy?
        #hdri = hdri.asDomain(ImgDomain.sRGB)
        self._processed_hdri = ImgBuffer(img=cv.GaussianBlur(hdri.get(), (blur_size, blur_size), -1))
        #hdri = hdri.asDomain(ImgDomain.Lin) # Conversion back
        

    ### Functions for samling light values ###

    def sampleHdri(self, longitude_offset=0):
        res_y, res_x = self._processed_hdri.get().shape[:2]
        for light in self._config:
            # Sample point in HDRI
            latlong = light['latlong']
            x = int(res_x * (360 - (latlong[1]+longitude_offset) % 360) / 360.0) # TODO: Is round here wrong? Indexing error when rounding up on last value!
            y = int(round(res_y/2 - res_y * latlong[0]/180.0))
            self._lightVals[light['id']] = self._processed_hdri[x, y]
    
    def sampleWithUV(self, f):
        for light in self._config:
            sample = f(light['uv'])
            self._lightVals[light['id']] = sample
    
    def sampleWithLatLong(self, f):
        for light in self._config:
            sample = f(light['latlong'])
            self._lightVals[light['id']] = sample

    # TODO!
    #def getLightDict(self, domain=ImgDomain.Lin, as_int=True):
    #    if as_int:
    #        return [light.asDomain(domain).asInt().get()]
    def getLights(self):
        return self._lightVals

    def writeLights(self):
        self._lights.setLights(self._lightVals)
        self._lights.write()

    ### Light functions ###

    def setTop(self, latitude = 60, brightness = DMX_MAX_VALUE):
        # Sample lights
        self.sampleWithLatLong(lambda latlong: ImgBuffer.FromPix(brightness) if latlong[0] > latitude else ImgBuffer.FromPix(0))

        # Write DMX values
        self.writeLights()
    
    def setNth(self, nth, brightness = DMX_MAX_VALUE):
        random.seed()
        self._lights.reset()
        for light in self._config:
            if random.randrange(0, nth) == 0:
                self._lightVals[light['id']] = ImgBuffer.FromPix(brightness)
        self.writeLights()
        #self._mask = [light['id'] for i, light in enumerate(self._config) if i % nth == 0] # TODO: This way every nth is lit and not random
    
    #TODO: Move to renderer
    def generateLightingFromSequence(self, img_seq: Sequence, longitude_offset=0) -> ImgBuffer:
        # Hier kannst du einsteigen, Iris :)
        # img_seq: Alle Bilder der einzelnen Lampen
        # self._processed_hdri: geblurtes HDRI

        generated = ImgBuffer(domain=ImgDomain.Lin)
        res_y, res_x = self._processed_hdri.get().shape[:2]

        for id, img in img_seq:
            # Test if config entry is valid -> configuration might be incomplete!

            if self._config[id] is not None:
                # ID ist Lampen ID, entspricht der ID der config
                latlong = self._config[id]['latlong'] # -> Koordinaten der Lampe
                img = img.asDomain(ImgDomain.Lin, as_float=True) # -> Bild als Linear

                # HDRI sampling
                x = int(res_x * (360 - (latlong[1]+longitude_offset) % 360) / 360.0) # TODO: Is round here wrong? Indexing error when rounding up on last value!
                y = int(round(res_y/2 - res_y * latlong[0]/180.0))
                rgb_factor = self._processed_hdri[x, y]

                if not generated.hasImg():
                    generated.set(img.get() * rgb_factor.get())
                else:
                    generated.set(generated.get() + img.get() * rgb_factor.get())

        generated.set(generated.get() / len(img_seq)) # Normalize brightness
        return generated # Frame wird returned und in domectl.py gespeichert


    ### Functions to generate images with mapping of sampled lights ###
    
    def generateUVMapping(self, image=None) -> ImgBuffer:
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
        
    def generateLatLongMapping(self, image=None) -> ImgBuffer:
        # Generate RGB image with aspect ratio 2:1
        res_x, res_y = (self.img_res_base * 2, self.img_res_base)
        if image is None:
            image = ImgBuffer(img=np.full((res_y, res_x, 3), self.img_background, dtype='uint8'), domain=ImgDomain.sRGB)
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
            cv.circle(image.get(), (x, y), light_radius, value, cv.FILLED) # TODO value is gray or RGB sometimes
            # Outline
            cv.circle(image.get(), (x, y), light_radius, (255, 255, 255), 1)

        return image

        