from ...hw.calibration import *
from ...data import *
from ...utils import *
from ...utils import ti_base as tib

from .pseudoinverse import PseudoinverseFitter

import taichi as ti
import taichi.math as tm
import taichi.types as tt


# Bivariant hemispherical harmonics fitter
class SHFitter(PseudoinverseFitter):
    name = "Spherical Harmonics Fitter"
    
    def __init__(self, settings):
        super().__init__(settings)
        # Settings: Limit polynom degree
        self._degree = max(2, min(6, settings['degree'])) if 'degree' in settings else 3
    
    def getCoefficientCount(self) -> int:
        """Returns number of coefficients"""
        # Coefficent count is number of all equations for a degree and the degrees before
        return (self._degree + 1)**2
            
    def fillLightMatrix(self, line, lightpos: LightPosition):
        u, v = lightpos.getLL()
        
        for coeff_num in range(len(line)):
            l = math.floor(math.sqrt(coeff_num))
            m = coeff_num - l * (l + 1)
            # l & m are parameters of the degree of the harmonics in the shape of:
            # (0,0), (1,-1), (1,0), (1,1), (2,-2), (2,-1), ...
            line[num] = H(l, m, u, v)
            
        
    # Helper function for HSH calculation
    def SH(l, m, theta, phi) -> float:
        """Spherical harmonics for the given degrees l & m and and spherical coordinates"""
        if m == 0:
            return SHFitter.K(l, 0) * SHFitter.P(l, 0, theta)
        elif m < 0:
            return root_two * SHFitter.K(l, m) * math.sin(-m * phi) * SHFitter.P(l, -m, theta)
        else:
            return root_two * SHFitter.K(l, m) * math.cos(m * phi) * SHFitter.P(l, m, theta)
        
    def K(l: int, m: int) -> float:
        return math.sqrt(((2*l + 1) / math.tau) * (factorial(-m if l - m < 0 else m) / factorial(-m if l + m < 0 else m)))

    def P(l: int, m: int, x: float) -> float:
        if l == 0 and m == 0:
            return 1
        elif l == 1 and m == 0:
            return x
        elif l == 1 and m == 1:
            return -math.sqrt(1.0 - x * x)
        elif l == m:
            return factorial2(2 * m - 1) * math.sqrt(math.pow(1 - x * x, m))
        elif m == l - 1:
            return (2 * m + 1) * x * SHFitter.P(m, m, x)
        else:
            return ((2 * l - 1) * x * SHFitter.P(l - 1, m, x) - (l + m - 1) * SHFitter.P(l - 2, m, x)) / (l - m)
        
