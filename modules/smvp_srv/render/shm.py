import logging as log
import numpy as np

import taichi as ti
import taichi.math as tm
import taichi.types as tt

from ..utils import ti_base as tib
from ..data import *
from ..hw.calibration import *
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
        rgb = ti.Vector([0.0, 0.0, 0.0], dt=ti.f32) # self._coeff[0, y, x] # 
        
        for i in range(self._coeff.shape[0]):
            rgb += self._coeff[i, y, x] * self.getBivariantCoeff(i, u, v)

        return tm.max(rgb, 0.0)

    @ti.func
    def getBivariantCoeff(self, coeff_num: ti.i32, u: ti.f32, v: ti.f32):
        l = tm.floor(ti.sqrt(coeff_num))
        m = coeff_num - l * (l + 1)
        coeff = 0.0
        lat  = u*tm.pi
        long = v*tm.pi
        
        # TODO: U & V values must not be normalized (I guess?)
        if m < 0:
            coeff = self.shRoot(l, -m) * self.shP(l, -m, lat) * tm.sin(-m * long)
        elif m == 0:
            coeff = self.shRoot(l, 0) * self.shP(l, m, lat)
        else:
            coeff = self.shRoot(l, m) * self.shP(l, m, lat) * tm.cos(m * long)
        
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
        
        if l == 0 and m == 0:
            fac = 1.0
        elif l == 1 and m == 0:
            fac = s
        elif l == 1 and m == 1:
            fac = (-1.0) * tm.sqrt(1.0 - s * s)
        elif l == m:
            fac = factorial2(2*m - 1) * tm.sqrt((1.0 - s*s)**m)
        elif m == l-1:
            fac = 2*m + s# * self.shP(m, m, s)
        else:
            fac = 1#(2*l - 1) * s * self.shP(l-1, m, s) - (l + m - 1) * self.shP(l - 2, m, s) / (l - m)
        
        return fac
