from .pseudoinverse import PseudoinverseFitter
from ...hw.calibration import *

import taichi as ti
import taichi.math as tm
import taichi.types as tt
from ...utils import ti_base as tib

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
