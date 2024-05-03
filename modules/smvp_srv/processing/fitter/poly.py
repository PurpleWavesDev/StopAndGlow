from ...hw.calibration import *
from ...data import *
from ...utils import ti_base as tib

from .pseudoinverse import PseudoinverseFitter

import taichi as ti
import taichi.math as tm
import taichi.types as tt

class PolyFitter(PseudoinverseFitter):
    name = "Polynomial Fitter"
    
    def __init__(self, settings):
        super().__init__(settings)
        # Settings: Limit polynom degree
        self._degree = max(2, min(6, GetSetting(settings, 'degree', 3)))
    
    def getCoefficientCount(self) -> int:
        """Returns number of coefficients"""
        return (self._degree+1)*(self._degree+2) // 2
        #return (degree+1)**2 // 2 + (degree+1) // 2
            
    def fillLightMatrix(self, line, lightpos: LightPosition):
        u, v = lightpos.get(CoordSys(self._coord_sys), True)
        # Start with degree 0 and 1 
        line[0] = 1
        line[1] = u
        line[2] = v
        # Higher degrees
        idx = 3
        for n in range(2, self._degree+1):
            for i in range(n+1):
                line[idx] = u**(n-i) * v**i
                idx += 1
