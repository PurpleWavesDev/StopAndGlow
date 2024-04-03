from .pseudoinverse import PseudoinverseFitter
from ...hw.calibration import *

import taichi as ti
import taichi.math as tm
import taichi.types as tt
from ...utils import ti_base as tib

class NormalFitter(PseudoinverseFitter):
    name = "Normalmap Fitter"
    
    def __init__(self, settings = {}):
        super().__init__(settings)
        # Settings
        #self._scale_positive = settings['scale_to_positive'] if 'scale_to_positive' in settings else True
    
    def getCoefficientCount(self) -> int:
        """Returns number of coefficients"""
        return 3
            
    def fillLightMatrix(self, line, coord):
        u, v = coord
        line = [u, v, 1]
    
# TODO?
@ti.kernel
def sampleLight(pix: ti.types.ndarray(dtype=tt.vector(3, ti.f32), ndim=2), coeff: ti.template(), u: ti.f32, v: ti.f32):
    for y, x in pix:
        pix[y, x] = [coeff[0, y, x][0], coeff[1, y, x][0], 0.5]
