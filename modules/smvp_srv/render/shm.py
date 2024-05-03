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
        rgb = self._coeff[0, y, x]
        
        for i in range(_number_of_coefficients):
            rgb += v4tmp0[i % 4] * getBivariantCoeff(i)

        return tm.max(rgb, 0.0)

    @ti.func
    def getBivariantCoeff(coeff_num: ti.i32):
        l = tm.floor(ti.sqrt(coeff_num))
        m = coeff_num - l * (l + 1)

        if m == 0:
            hshK(l, 0)
            hshP(s, l, m)
        else:
            if m < 0:
                root_two * hshK(l, m) * sin(-m * ftmp2)
                hshP(s, l, -m)
            else:
                root_two * hshK(l, m) * cos(m * ftmp2)
                hshP(s, l, m)

