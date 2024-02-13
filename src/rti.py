import logging as log
import numpy as np
from numpy.typing import ArrayLike
import math

import cv2 as cv

import taichi as ti
#from numba import njit, prange, types
#from numba.typed import Dict

from src.imgdata import *
from src.sequence import *
from src.config import *

class Rti:
    def __init__(self, resolution=(0,0)):
        self._res_x = resolution[0]
        self._res_y = resolution[1]
        
        self._factors = np.zeros((0,))
        self._frames = dict()#Dict.empty(
            #key_type=types.int32,
            #value_type=types.float32[:])

        
    def calculate(self, img_seq: Sequence, config: Config, num_factors=6):
        # Load images first
        for id, img in img_seq:
            self._frames[id] = img.asDomain(ImgDomain.Lin, as_float=True).get()
            img.unload()
        
        # Fill lights dict for numba
        lights = dict()#Dict.empty(
            #key_type=types.int32,
            #value_type=types.float32[:])
        for light in config:
            id = light['id']
            u, v = Rti.Latlong2UV(light['latlong'])

            if frames[id] is not None:
                # Fill matrix with coordinate 
                u, v = light
                A = np.vstack((A, np.array([1, u, v, u*v, u**2, v**2])))

        
        # Iterate over pixels
        #@njit(parallel=True)
        def parallel_calc(frames, lights, res_x, res_y):
            factors = np.zeros((6, res_y, res_x, 3))
            for y in range(res_y):
                for x in range(res_x):
                    A = np.zeros((0,6))
                    vec_rgb = np.zeros((0, 3))
                    
                    # Iterate over lights
                    ## Die schleife nach vorne!
                    for id, light in lights.items():
                        if frames[id] is not None:
                            # Fill matrix with coordinate 
                            u, v = light
                            A = np.vstack((A, np.array([1, u, v, u*v, u**2, v**2])))
                            # Fill vector with pixel values
                            vec_rgb = np.vstack((vec_rgb, frames[id][y][x]))
                            
                    # We want to solve following equation: A x = b; where
                    #   x is the vector of the 6 unknown factors
                    #   b are the pixel values (RGB)
                    # Equation is over determined, we can use the least-squares solution
                    # A muss invertiert werden! Alles vor der Schleife
                    #np.linalg.inv()
                    result, _, _, _ = np.linalg.lstsq(A, vec_rgb, rcond=None)
                    for row in enumerate(result):
                        factors[row[0]][y][x] = row[1]
                        
            return factors
        
        self._factors = parallel_calc(self._frames, lights, self._res_x, self._res_y)
                
                ## SVD decomposition replaces this problem with: U diag(s) Vh x = b
                ## Compute SVD
                #U,s,Vh = np.linalg.svd(mat_a)
                ## U diag(s) Vh x = b <=> diag(s) Vh x = U.T b = c
                #c = np.dot(U.T, vec_b)
                ## diag(s) Vh x = c <=> Vh x = diag(1/s) c = w (trivial inversion of a diagonal matrix)
                #w = np.dot(np.diag(1/s), c)
                ## Vh x = w <=> x = Vh.H w (where .H stands for hermitian = conjugate transpose)
                #x = np.dot(Vh.conj().T, w)
    
    def load(self, rti_seq: Sequence):
        #self._factors = np.zeros((0, self._res_y, self._res_x, 3))
        self._factors = np.stack([frame[1].get() for frame in rti_seq], axis=0)
    
    def get(self) -> Sequence:
        seq = Sequence()
        
        for i in range(6):
            seq.append(ImgBuffer(img=self._factors[i], domain=ImgDomain.Lin), i)
        
        return seq
    
    def sampleLight(self, light_pos) -> ImgBuffer:
        image = ImgBuffer(img=np.zeros((self._res_y, self._res_x, 3)), domain=ImgDomain.Lin)
        
        u, v = Rti.Latlong2UV(light_pos)
        
        for x in range(self._res_x):
            for y in range(self._res_y):
                rgb = self.a(0)[y, x] + self.a(1)[y, x]*u + self.a(2)[y, x]*v + self.a(3)[y, x]*u*v + self.a(4)[y, x]*u**2 + self.a(5)[y, x]*v**2
                image.setPix((x, y), rgb)
        
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
