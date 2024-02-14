import logging as log
import numpy as np
from numpy.typing import ArrayLike
import math

import cv2 as cv

#import taichi as ti
#import taichi.math as tm
#from numba import njit, prange, types
#from numba.typed import Dict

from src.imgdata import *
from src.sequence import *
from src.config import *
import src.rti_taichi as rtaichi

SIX_FACTORS = lambda u, v: np.array([1, u, v, u*v, u**2, v**2])
#SEVEN_FACTORS = lambda u, v: np.array([1, u, v, u*v, u**2, v**2, u**2 * v + ])
EIGTH_FACTORS = lambda u, v: np.array([1, u, v, u*v, u**2, v**2, u**2 * v, v**2 * u])


class Rti:
    def __init__(self, resolution=(0,0)):
        self._res_x = resolution[0]
        self._res_y = resolution[1]
        
        self._factors = np.zeros((0,))
        
    def calculate(self, img_seq: Sequence, config: Config, num_factors=8):
        # Generate matrix inverse and load frames
        frames = list()
        img_keys = img_seq.getKeys()
        A = np.zeros((0,num_factors))
        # Iterate over lights
        for light in config:
            id = light['id']
            # Check if ID is in image sequence            
            if id in img_keys:
                # Load frames
                frames.append(img_seq[id].asDomain(ImgDomain.Lin, as_float=True).get())
                img_seq[id].unload()
                # Fill matrix with coordinate 
                u, v = Rti.Latlong2UV(light['latlong'])
                A = np.vstack((A, EIGTH_FACTORS(u, v))) # TODO
        # Calculate inverse
        A = np.linalg.pinv(A)
        
        # Empty array for factors
        self._factors = np.zeros((num_factors, self._res_y, self._res_x, 3))
        # Iterate over pixels
        for y in range(self._res_y):
            for x in range(self._res_x):
                vec_rgb = np.zeros((0, 3))
                
                # Iterate over frames
                for frame in frames:
                    vec_rgb = np.vstack((vec_rgb, frame[y][x]))
                
                # Calculate result and apply to factor array
                result = A @ vec_rgb
                for row in enumerate(result):
                    self._factors[row[0]][y][x] = row[1]
                    
    
    def load(self, rti_seq: Sequence):
        #self._factors = np.zeros((0, self._res_y, self._res_x, 3))
        self._factors = np.stack([frame[1].get() for frame in rti_seq], axis=0)
    
    def get(self) -> Sequence:
        seq = Sequence()
        
        for i in range(self._factors.shape[0]):
            seq.append(ImgBuffer(img=self._factors[i], domain=ImgDomain.Lin), i)
        
        return seq
    
    def sampleLight(self, light_pos) -> ImgBuffer:
        image = ImgBuffer(img=np.zeros((self._res_y, self._res_x, 3)), domain=ImgDomain.Lin)
        
        u, v = Rti.Latlong2UV(light_pos)
        
        for x in range(self._res_x):
            for y in range(self._res_y):
                #rgb = self.a(0)[y, x] + self.a(1)[y, x]*u + self.a(2)[y, x]*v + self.a(3)[y, x]*u*v + self.a(4)[y, x]*u**2 + self.a(5)[y, x]*v**2
                rgb = self.a(0)[y, x] + self.a(1)[y, x]*u + self.a(2)[y, x]*v + self.a(3)[y, x]*u*v + self.a(4)[y, x]*u**2 + self.a(5)[y, x]*v**2 + self.a(6)[y, x]*u**2 * v + self.a(7)[y, x]*v**2 * u
                image.setPix((x, y), rgb)
        
        return image
    
    def sampleHdri(self, hdri) -> ImgBuffer:
        image = ImgBuffer()
        
        return image
    
    def sampleNormals(self) -> ArrayLike:
        normals = np.zeros((self._res_y, self._res_x, 3))
        
        return normals


    def launchViewer(self, scale=1):
        rtaichi.launchViewer(res=(int(self._res_x * scale), int(self._res_y * scale)))
    
    def a(self, factor) -> ArrayLike:
        return self._factors[factor]
    
    # Static functions
    def Latlong2UV(latlong) -> [float, float]:
        """Returns Lat-Long coordinates in the range of -1 to 1"""
        return (latlong[0] / 90, latlong[1]/180 - 1)

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
