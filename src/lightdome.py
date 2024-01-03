import logging as log
import numpy as np
import math

import cv2 as cv

from src.imgdata import *
from src.config import *


class Lightdome:
    def __init__(self, config: Config):
        self._config = config
        self._imgResBase = 1000
        self._imgBackground = 50
    
    def sampleHdri(self, hdri: ImgBuffer):
        res_x, res_y = (hdri.shape[1], hdri.shape[0])
        
        blur_factor=2 # TODO: Calculate somehow?
        # Blur HDRI to reduce errors
        hdri = cv.blur(hdri, res_y*blur_factor/100)
        
    def sampleHdriBw(self, hdri: ImgBuffer):
        return self.sampleHdri(hdri.RGB2Gray())
    
    def sampleUV(self, f):
        pass
    
    def sampleLatLong(self, f):
        pass
    
    def generateUV(self):
        # Generate RGB image and draw blue circle for sphere
        img_uv = np.full((_imgResBase, _imgResBase, 3), _imgBackground, dtype='uint8')
        cv.circle(img_uv, (_imgResBase/2, _imgResBase/2), _imgResBase/2, (0, 0, 255), 2)
        
        for light_entry in self._config:
            cv.circle(img_uv, (int(500+500*light_entry['uv'][0]), int(500-500*light_entry['uv'][1])), 6, (0, 255, 0), 2)
            
        #Lightdome.imgSave(img_uv, "lightdome_uv")
        
    def generateLatLong(self):
        # Generate RGB image with aspect ratio 2:1
        img_latlong = np.full((_imgResBase, _imgResBase*2, 3), _imgBackground, dtype='uint8')
        
        for light_entry in self._config:
            cv.circle(img_latlong, (int(2000*light_entry['latlong'][1]/360), int(500-500*light_entry['latlong'][0]/90)), 6, (0, 255, 0), 2)

        #Lightdome.imgSave(img_latlong, "lightdome_latlong")
    
    
    # TODO: Move function somewhere else
    def imgSave(img, name, img_format=ImgFormat.PNG):
        BASE_PATH_EVAL='../HdM_BA/data/eval'
        img = ImgBuffer(img=img, path=os.path.join(BASE_PATH_EVAL, name))
        img.save(img_format)
        