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
        self._degree = max(1, min(2, settings['degree'])) if 'degree' in settings else 1
    
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
            #line[coeff_num] = SHFitter.SH(l, m, u, v)
            line[coeff_num] = SHFitter.SHHardCoded(l, m, x, y, z, lat, long)
            
        
    # Helper function for Spherical Harmonics calculation
    
    def SHHardCoded(l, m, x, y, z, lat, long) -> float:
        match l:
            case 0:
                return math.sqrt(1/(4*math.pi))
            case 1:
                match m:
                    case -1:
                        #return math.sqrt(3/(4*math.pi)) * -math.cos(lat) * math.cos(long)
                        return math.sqrt(3/(4*math.pi)) * y
                    case 0:
                        #return math.sqrt(3/(4*math.pi)) * math.sin(lat)
                        return math.sqrt(3/(4*math.pi)) * z
                    case 1:
                        #return math.sqrt(3/(4*math.pi)) * -math.cos(lat) * -math.sin(long)
                        return math.sqrt(3/(4*math.pi)) * x
            case 2:
                match m:
                    case -2:
                        #return math.sqrt(15/(16*math.pi)) * (-math.cos(lat))**2 * math.cos(2*long)
                        return math.sqrt(15/(4*math.pi)) * x*y
                    case -1:
                        #return math.sqrt(15/(16*math.pi)) * -math.cos(2*lat) * math.cos(long)
                        return math.sqrt(15/(4*math.pi)) * y*z
                    case 0:
                        #return math.sqrt(5/(16*math.pi)) * (3*math.sin(lat)**2 - 1)
                        return math.sqrt(5/(16*math.pi)) * (3*z*z - 1)
                    case 1:
                        #return math.sqrt(15/(16*math.pi)) * -math.cos(2*lat) * -math.sin(long)
                        return math.sqrt(15/(4*math.pi)) * x*z
                    case 2:
                        #return math.sqrt(15/(4*math.pi)) * (-math.cos(lat))**2 * -math.sin(2*long)
                        return math.sqrt(15/(4*math.pi)) * (x*x - y*y)
    
    ## TODO: Unused
    def SH(l, m, theta, phi) -> float:
        """Spherical harmonics for the given degrees l & m and and spherical coordinates"""
        if m < 0:
            return SHFitter.RootFactor(l, -m) * SHFitter.P(l, -m, -math.sin(theta)) * math.sin(-m * phi) # -sin to cos oä?
        elif m == 0:
            return SHFitter.RootFactor(l, 0) * SHFitter.P(l, 0, -math.sin(theta))
        else:
            return SHFitter.RootFactor(l, m) * SHFitter.P(l, m, -math.sin(theta)) * math.cos(m * phi)

    def RootFactor(l, m) -> float:
        fac = (2*l + 1) / (4*math.pi)
        if m != 0:
            fac *= 2 * (factorial(l-m)) / (factorial(l+m))
        return math.sqrt(fac)

    def P(l: int, m: int, x: float) -> float:
        """associated Legendre polynomials"""
        if l == 0 and m == 0:
            return 1.0
        elif l == 1 and m == 0:
            return x
        elif l == 1 and m == 1:
            return -math.sqrt(1.0 - x*x)
        elif l == m:
            return factorial2(2*m - 1) * math.sqrt((1.0 - x*x)**m)
        elif l-1 == m:
            return (2*m + 1) * x * SHFitter.P(m, m, x)
        else:
            return ((2*l - 1) * x * SHFitter.P(l-1, m, x) - (l + m - 1) * SHFitter.P(l-2, m, x)) / (l-m) # Minus therm wrong? is 1/2 should be 1

