from src.renderer.fitter.pseudoinverse import PseudoinverseFitter
from src.config import *

import taichi as ti
import taichi.math as tm
import taichi.types as tt
import src.ti_base as tib

class PolyFitter(PseudoinverseFitter):
    name = "Polynomial Fitter"
    
    def __init__(self, settings):
        super().__init__(settings)
        # Settings: Limit polynom order
        self._order = max(2, min(6, settings['order'])) if 'order' in settings else 3
    
    def getCoefficientCount(self) -> int:
        """Returns number of coefficients"""
        return (self._order+1)*(self._order+2) // 2
        #return (order+1)**2 // 2 + (order+1) // 2
            
    def fillLightMatrix(self, line, coord):
        u, v = coord
        # Start with order 0 and 1 
        line[0] = 1
        line[1] = u
        line[2] = v
        # Higher orders
        idx = 3
        for n in range(2, self._order+1):
            for i in range(n+1):
                line[idx] = u**(n-i) * v**i
                idx += 1
    
    def renderLight(self, buffer, coords, slices=1):
        u, v = coords
        sampleLight(buffer, self._coefficients, u, v)
    
    def renderHdri(self, buffer, hdri, rotation, slices=1):
        sampleHdri(buffer, inverse, hdri, rotation)


@ti.kernel
def sampleLight(pix: ti.types.ndarray(dtype=tt.vector(3, ti.f32), ndim=2), coeff: ti.template(), u: ti.f32, v: ti.f32):
    for y, x in pix:
        pix[y, x] = sampleUV(coeff, y, x, u, v)
        # Exposure correction (?)
        pix[y, x] *= 10

        
@ti.kernel
def sampleHdri(pix: ti.types.ndarray(dtype=tt.vector(3, ti.f32), ndim=2), coeff: ti.template(), hdri: ti.template(), rotation: ti.f32):
    samples_y = 10
    samples_x = 40
    rot = 1 - rotation
    for y, x in pix:
        pix[y, x] = 0
        # TODO: Smarter sampling: Should sample on coordinates that are the the brightest for a pixel
        for yy, xx in ti.ndrange(samples_y, samples_x):
            u = yy / (samples_y) * 0.3 + 0.6
            v = xx / samples_x
            pix[y, x] += sampleUV(coeff, y, x, u, v) / (10) * \
                hdri[ti.cast(u*hdri.shape[0], ti.i32), ti.cast(((v+rot) * hdri.shape[1]) % hdri.shape[1], ti.i32)]

@ti.func
def sampleUV(A: ti.template(), y: ti.i32, x: ti.i32, u: ti.f32, v: ti.f32):
    rgb = A[0, y, x]
    #n = 1, 2, 3, 4, 5, 6, 7, 8, 9
    #a = 1, 1, 2, 2, 2, 3, 3, 3, 3
    #b = 0, 1, 0, 1, 2, 0, 1, 2, 3
    
    rgb += sampleSum(A, y, x, u, v, 1, 1)        
    if A.shape[0] >= 6:
        rgb += sampleSum(A, y, x, u, v, 3, 2)
    if A.shape[0] >= 10:
        rgb += sampleSum(A, y, x, u, v, 6, 3)
    if A.shape[0] >= 15:
        rgb += sampleSum(A, y, x, u, v, 10, 4)
    if A.shape[0] >= 21:
        rgb += sampleSum(A, y, x, u, v, 15, 5)
    if A.shape[0] >= 28: 
        rgb += sampleSum(A, y, x, u, v, 21, 6)
        
    return rgb

@ti.func
def sampleSum(A, y, x, u, v, offset, a):
    rgb = A[offset, y, x] * u**(a)
    for i in range(1, a+1):
        rgb += A[offset+i, y, x] * u**(a-i) * v**i
    return rgb