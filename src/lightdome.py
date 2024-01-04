import logging as log
import numpy as np
import math

import cv2 as cv

from src.imgdata import *
from src.config import *


class Lightdome:
    def __init__(self, config: Config = None):
        self.img_res_base = 1000
        self.img_background = 50
        self.blur_size = 2
        self._lightVals = dict()
        if config is not None:
            self.setConfig(config)
        
    def setConfig(self, config: Config):
        self._config = config
        self._lightVals.clear()
    
    def sampleHdri(self, hdri: ImgBuffer):
        res_y, res_x = hdri.get().shape[:2]
        
        # Blur HDRI to reduce errors
        #hdri.set(cv.blur(hdri.get(), self.blur_size*res_y/100))
        for light in self._config:
            #print(light)
            # Sample point in HDRI
            latlong = light['latlong']
            img_coord = [ int(res_x * latlong[1]/360.0 + 0.5), int(res_y * latlong[0]/180.0 + res_y/2 + 0.5) ]
            sample = hdri.get()[img_coord[1]][img_coord[0]]
            print(latlong, img_coord, sample)
            
        
    def sampleHdriBw(self, hdri: ImgBuffer):
        return self.sampleHdri(hdri.RGB2Gray())
    
    def sampleUV(self, f):
        pass
    
    def sampleLatLong(self, f):
        pass
    
    def generateUV(self):
        # Generate RGB image and draw blue circle for sphere
        img_uv = np.full((self.img_res_base, self.img_res_base, 3), self.img_background, dtype='uint8')
        cv.circle(img_uv, (self.img_res_base/2, self.img_res_base/2), self.img_res_base/2, (0, 0, 255), 2)
        
        for light_entry in self._config:
            cv.circle(img_uv, (int(500+500*light_entry['uv'][0]), int(500-500*light_entry['uv'][1])), 6, (0, 255, 0), 2)
            
        #Lightdome.imgSave(img_uv, "lightdome_uv")
        
    def generateLatLong(self):
        # Generate RGB image with aspect ratio 2:1
        img_latlong = np.full((self.img_res_base, self.img_res_base*2, 3), self.img_background, dtype='uint8')
        
        for light_entry in self._config:
            cv.circle(img_latlong, (int(2000*light_entry['latlong'][1]/360), int(500-500*light_entry['latlong'][0]/90)), 6, (0, 255, 0), 2)

        #Lightdome.imgSave(img_latlong, "lightdome_latlong")
    
    
    # TODO: Move function somewhere else
    def imgSave(img, name, img_format=ImgFormat.PNG):
        BASE_PATH_EVAL='../HdM_BA/data/eval'
        img = ImgBuffer(img=img, path=os.path.join(BASE_PATH_EVAL, name))
        img.save(img_format)
        