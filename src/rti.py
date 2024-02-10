import logging as log
import numpy as np
from numpy.typing import ArrayLike
import math

import cv2 as cv

from src.imgdata import *
from src.sequence import *
from src.config import *

class Rti:
    def __init__(self, resolution=(0,0)):
        self._res_x = resolution[0]
        self._res_y = resolution[1]
        
        self._factors = np.zeros((6, self._res_y, self._res_x, 3))
        
    
    def calculate(self, img_seq: Sequence, config: Config, num_factors=6):
        # Iterate over pixels
        for x in range(self._res_x):
            for y in range(self._res_y):
                # Iterate over lights and fill matrix
                for light in config:
                    id = light['id']
                    u, v = Rti.Latlong2UV(light['latlong'])
                    
                    if img_seq[id] is not None:
                        img = img_seq[id].asDomain(ImgDomain.Lin, as_float=True).get()
                        
                # Solve factors for pixel
            
    
    def load(self, rti_seq: Sequence):
        pass
    
    def get(self, path) -> Sequence:
        seq = Sequence()
        
        return seq
    
    def sampleLight(self, light_pos) -> ImgBuffer:
        image = ImgBuffer()
        
        u, v = Rti.Latlong2UV(light_pos)
        
        for x in range(self._res_x):
            for y in range(self._res_y):
                rgb = self.a(0)[y, x] + self.a(1)[y, x]*u + self.a(2)[y, x]*v + self.a(3)[y, x]*u*v + self.a(4)[y, x]*u**2 + self.a(5)[y, x]*v**2
                image.setPixel(x, y, rgb)
        
        return image
    
    def sampleHdri(self, hdri) -> ImgBuffer:
        image = ImgBuffer()
        
        return image
    
    def sampleNormals(self) -> ArrayLike:
        normals = np.zeros((self._res_y, self._res_x, 3))
        
        return normals
    
    def a(self, factor) -> ArrayLike:
        return self._factors[factor]
    
    # Static functions
    def Latlong2UV(latlong) -> [float, float]:
        """Returns Lat-Long coordinates in the range of -1 to 1"""
        return (latlong[0] / 180, latlong[1]/180 - 1)

# OpenExr Sample Function    
#import OpenEXR as exr
#
#def read_depth_exr_file(filepath: Path):
#    exrfile = exr.InputFile(filepath.as_posix())
#    raw_bytes = exrfile.channel('B', Imath.PixelType(Imath.PixelType.FLOAT))
#    depth_vector = numpy.frombuffer(raw_bytes, dtype=numpy.float32)
#    height = exrfile.header()['displayWindow'].max.y + 1 - exrfile.header()['displayWindow'].min.y
#    width = exrfile.header()['displayWindow'].max.x + 1 - exrfile.header()['displayWindow'].min.x
#    depth_map = numpy.reshape(depth_vector, (height, width))
#    return depth_map
