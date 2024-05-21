import logging as log
import numpy as np

import taichi as ti
import taichi.math as tm
import taichi.types as tt

from ..utils import ti_base as tib
from ..data import *
from .bsdf import BSDF


class ShmBsdf(BSDF):
    def load(self, data: Sequence, calibration: Calibration, data_key: str, settings={}) -> bool:
        rti_seq = data.getDataSequence(data_key)
        if len(rti_seq) > 0:
            # Load data into fields
            res_x, res_y = rti_seq.get(0).resolution()
            self._coeff = ti.field(tib.pixvec)
            ti.root.dense(ti.ijk, (len(rti_seq), res_y, res_x)).place(self._coeff) # TODO ijk ? Pack pixels of all images together
            # Copy
            arr = np.stack([frame.get() for _, frame in rti_seq], axis=0)
            self._coeff.from_numpy(arr)
            
            # Set coordinate system switch
            self.coord_sys = GetSetting(settings, 'coordinate_system', CoordSys.LatLong)
            return True
        return False
    
    
    @ti.func
    def sample(self, x: ti.i32, y: ti.i32, u: ti.f32, v: ti.f32) -> tib.pixvec:
        # Pixel buffer
        rgb = ti.Vector([0.0, 0.0, 0.0], dt=ti.f32)
        # Convert UV to 
        lat  = pi_by_2 - u*pi_by_2
        long = v*tm.pi + tm.pi
        
        for i in range(self._coeff.shape[0]):
            l = tm.floor(ti.sqrt(i))
            m = i - l * (l + 1)
            rgb += self._coeff[i, y, x] * self.shHardCoded(l, m, lat, long)
            # TODO: Slow and not really working
            #rgb += self._coeff[i, y, x] * self.getBivariantCoeff(i, lat_conv, long)

        return tm.max(rgb, 0.0)
    
    #@ti.func
    #def sph_harm(self, m, n, theta, phi): # l, m -> m, n
    #    m_abs = ti.abs(m)
    #    c_val = pmv(m_abs, n, ti.cos(phi))
    #    if m < 0:
    #        c_val *= ti.pow(-1, m_abs) * self.poch(n + m_abs + 1, -2 * m_abs)
#
    #    c_val *= ti.sqrt((2*n + 1) * self.poch(n + m + 1, -2*m) / (4*ti.pi))
    #    c_val *= ti.exp(std::complex(0.0, m*theta))
#
    #    return c_val.real
    #
    #@ti.func
    #def poch(self, a: ti.f32, m: ti.f32) -> ti.f32:
    #    r = 1.0
    #    while (m >= 1.0):
    #        if a + m == 1:
    #            break
    #        
    #        m -= 1.0
    #        r *= (a + m)
    #        if r != tm.inf or r == 0:
    #            break
#
    #    while m <= -1.0:
    #        if a + m == 0:
    #            break
    #        r /= a + m
    #        m += 1.0
    #        if r != tm.inf or r == 0:
    #            break
#
    #    if m == 0:
    #        val = r
    #    elif a > 1e4 and ti.abs(m) <= 1:
    #        val = r * std::pow(a, m) *
    #               (1 + m * (m - 1) / (2 * a) + m * (m - 1) * (m - 2) * (3 * m - 1) / (24 * a * a) +
    #                m * m * (m - 1) * (m - 1) * (m - 2) * (m - 3) / (48 * a * a * a))
#
    #    elif self.is_nonpos_int(a + m) and not self.is_nonpos_int(a) and a + m != m:
    #        val = std::numeric_limits<double>::infinity()
    #    elif not self.is_nonpos_int(a + m) and detail::is_nonpos_int(a):
    #        val = 0
    #    else:
    #        val = r * std::exp(lgam(a + m) - lgam(a)) * gammasgn(a + m) * gammasgn(a)
#
    #    return val
    
    #@ti.func
    #def pmv(m: ti.f32, v: ti.f32, x: ti.f32) -> ti.f32:
    #m_int = ti.cast(m, ti.i32)
    #val = 0.0

    #val = specfun::lpmv(x, int_m, v);
    #SPECFUN_CONVINF("pmv", out);
    #return val
    #
    #@ti.func
    #def is_nonpos_int(self, x: ti.f32) -> ti.f32:
    #    return x <= 0 and x == ti.ceil(x) and ti.abs(x) < 1e13



    @ti.func
    def shHardCoded(self, l, m, lat: ti.f32, long: ti.f32) -> ti.f32:
        val = 0.0
        
        if l == 0:
            val = ti.sqrt(1/(4*math.pi))
        elif l == 1:
            if m == -1:
                val = ti.sqrt(3/(4*math.pi)) * tm.sin(lat) * tm.sin(long)
            elif m == 0:
                val = ti.sqrt(3/(4*math.pi)) * tm.cos(lat)
            else: # m == 1:
                val = ti.sqrt(3/(4*math.pi)) * tm.sin(lat) * tm.cos(long)
        elif l == 2:
            if m == -2:
                val = ti.sqrt(15/(16*math.pi)) * tm.sin(lat)**2 * tm.sin(2*long)
            if m == -1:
                val = ti.sqrt(15/(16*math.pi)) * tm.sin(2*lat) * tm.sin(long)
            elif m == 0:
                val = ti.sqrt(5/(16*math.pi)) * (3*tm.cos(lat)**2 - 1)
            elif m == 1:
                val = ti.sqrt(15/(16*math.pi)) * tm.sin(2*lat) * tm.cos(long)
            else: #if m == 2:
                val = ti.sqrt(15/(4*math.pi)) * tm.sin(lat)**2 * tm.cos(2*long)
        return val
    
    
    ## TODO: Unused approach for flexible amount of degrees (with limits)
    @ti.func
    def getBivariantCoeff(self, coeff_num: ti.i32, lat_conv: ti.f32, long: ti.f32):
        coeff = 0.0
        
        if m < 0:
            coeff = self.shRoot(l, -m) * self.shP(l, -m, lat_conv) * tm.sin(-m * long)
        elif m == 0:
            coeff = self.shRoot(l, 0) * self.shP(l, m, lat_conv)
        else:
            coeff = self.shRoot(l, m) * self.shP(l, m, lat_conv) * tm.cos(m * long)
        
        return coeff
    
    @ti.func
    def shRoot(self, l: ti.i32, m: ti.i32) -> ti.f32:
        fac = (2*l + 1) / (4*tm.pi)
        if m != 0:
            fac *= 2 * (factorial(l-m)) / (factorial(l+m))
        return ti.sqrt(fac)
    
    @ti.func
    def shP(self, l: ti.i32, m: ti.i32, s: ti.f32) -> ti.f32:
        fac = 1.0
        
        #if l-2 > m:
        #    # Double recursion for higher degrees, slow to compile and not working -> disallow higher degrees
        #    rec = (2*(l-1) - 1) * s * self.shPNoRec(l-2, m, s) - (l + m - 2) * self.shPNoRec(l-3, m, s) / (l - m - 1)
        #    fac = (2*l - 1) * s * rec - (l + m - 1) * self.shPNoRec(l-2, m, s) / (l - m)
        if l-1 > m:
            # Solves single recursions
            fac = (2*l - 1) * s * self.shPNoRec(l-1, m, s) - (l + m - 1) * self.shPNoRec(l-2, m, s) / (l - m)
        else:
            fac = self.shPNoRec(l, m, s)
        
        return fac
            
    @ti.func
    def shPNoRec(self, l: ti.i32, m: ti.i32, s: ti.f32) -> ti.f32:
        fac = 1.0
        if l == 0 and m == 0:
            pass # fac = 1.0
        elif l == 1 and m == 0:
            fac = s
        elif l == 1 and m == 1:
            fac = -tm.sqrt(1.0 - s*s)
        elif l == m:
            fac = factorial2(2*m - 1) * tm.sqrt((1.0 - s*s)**m)
        else: #if l-1 == m:
            fac = (2*m + 1) * s
            if m == 1: # l=2, m=1
                fac *= -tm.sqrt(1.0 - s*s)
            else: # l=3, m=2 and higher
                fac *= factorial2(2*m - 1) * tm.sqrt((1.0 - s*s)**m)
        # TODO: Tried to resolve recursions directly in function -> Not best solution
        #else:
        #    p1 = 1.0
        #    p2 = 1.0
        #    if l == 2:
        #        # l=2, m=0
        #        p1 = s # 1, 0
        #        #p2 = 1.0 # 0, 0
        #    elif l == 3:
        #        # l=3, m=1
        #        if m == 1:
        #            p1 = factorial2(2*m - 1) * tm.sqrt((1.0 - s*s)**m) # 2,1
        #            p2 = -tm.sqrt(1.0 - s*s) # 1,1
        #        # l=3, m=0
        #        else: #if m == 0:
        #            p1 = (2*(l-1) - 1) * s*s - (l + m - 2) / (l - m - 1) # 2,0 Recursion
        #            p2 = s # 1,0
        #    else: #if l == 4:
        #        # l=4, m=2
        #        if m == 2:
        #            p2 = factorial2(2*m - 1) * tm.sqrt((1.0 - s*s)**m) # 2,2
        #            p1 = (2*m + 1) * s * p2 # 3,2
        #        # l=4, m=1
        #        elif m == 1:
        #            p2 = factorial2(2*m - 1) * tm.sqrt((1.0 - s*s)**m) # 2,1
        #            p1 = (2*(l-1) - 1) * s * p2 - (l + m - 2) * -tm.sqrt(1.0 - s*s) / (l - m - 1) # 3,1 Recursion
        #        # l=4, m=0
        #        else: #if m == 0:
        #            p2 = (2*(l-1) - 1) * s*s - (l + m - 2) / (l - m - 1) # 2,0 Recursion
        #            p1 = (2*(l-1) - 1) * s * ((2*(l-2) - 1) * s*s - (l + m - 3) / (l - m - 2)) - (l + m - 2) * s / (l - m - 1) # 3,0 Double-Recursion
        #    #fac = (2*l - 1) * s * self.shP(l-1, m, s) - (l + m - 1) * self.shP(l-2, m, s) / (l - m)
        #    fac = (2*l - 1) * s * p1 - (l + m - 1) * p2 / (l - m)
        
        return fac
