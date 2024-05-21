from ...data import *
from ...utils import *
from ...utils import ti_base as tib

from .pseudoinverse import PseudoinverseFitter

import scipy
import numpy as np

import taichi as ti
import taichi.math as tm
import taichi.types as tt


# Bivariant hemispherical harmonics fitter
class SHFitter(PseudoinverseFitter):
    name = "Spherical Harmonics Fitter"
    
    def __init__(self, settings):
        super().__init__(settings)
        # Settings: Limit polynom degree
        self._degree = max(1, min(5, settings['degree'])) if 'degree' in settings else 1
        self._clamp = False
    
    def getCoefficientCount(self) -> int:
        """Returns number of coefficients"""
        # Coefficent count is number of all equations for a degree and the degrees before
        return (self._degree + 1)**2
            
    def fillLightMatrix(self, line, lightpos: LightPosition):
        #u, v = lightpos.getLL()
        x, y, z = lightpos.getXYZ()
        lat, long = lightpos.getLL()
        
        for coeff_num in range(len(line)):
            l = math.floor(math.sqrt(coeff_num))
            m = coeff_num - l * (l + 1)
            # l & m are parameters of the degree of the harmonics in the shape of:
            # (0,0), (1,-1), (1,0), (1,1), (2,-2), (2,-1), ...
            # scipy spherical harmonics are not rotated by 90° so doing this manually for m < 0
            if self._clamp:
                line[coeff_num] = max(0, scipy.special.sph_harm(m, l, long + (pi_by_2 if m < 0 else 0), pi_by_2-lat).real)
            else:
                line[coeff_num] = scipy.special.sph_harm(m, l, long + (pi_by_2 if m < 0 else 0), pi_by_2-lat).real
        

    def calc(self, latlong, coefficients):
        lat, long = latlong[:,0],latlong[:,1]
        val = coefficients[0]
        for i in range(1, len(coefficients)):
            l = math.floor(math.sqrt(i))
            m = i - l * (l + 1)
            # l & m are parameters of the degree of the harmonics in the shape of:
            # (0,0), (1,-1), (1,0), (1,1), (2,-2), (2,-1), ...
            # scipy spherical harmonics are not rotated by 90° so doing this manually for m < 0
            val += scipy.special.sph_harm(m, l, long*np.pi + (pi_by_2 if m < 0 else 0), pi_by_2 - lat*pi_by_2).real * coefficients[i]
            
        return np.fmax(val, np.zeros(val.shape))