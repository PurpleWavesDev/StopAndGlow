import logging as log
import numpy as np

import taichi as ti
import taichi.math as tm
import taichi.types as tt

from ..utils import ti_base as tib
from ..data import *
from .bsdf import BSDF


class PtmBsdf(BSDF):
    def load(self, sequence: Sequence) -> bool:
        rti_seq = sequence.getDataSequence(self._data_key)
        if len(rti_seq) > 0:
            # Load data into fields
            res_x, res_y = rti_seq.get(0).resolution()
            self._coeff = ti.field(tib.pixvec)
            ti.root.dense(ti.ijk, (len(rti_seq), res_y, res_x)).place(self._coeff) # TODO ijk ? Pack pixels of all images together
            # Copy
            arr = np.stack([frame.get() for _, frame in rti_seq], axis=0)
            self._coeff.from_numpy(arr)
            
            # Set coordinate system switch
            self.coord_sys = GetSetting(self._settings, 'coordinate_system', CoordSys.LatLong)
            return True
        return False
    
        ## Load metadata, get fitter
        #self._u_min, self._v_min = rti_seq.getMeta('latlong_min', (0, 0))
        #self._u_max, self._v_max = rti_seq.getMeta('latlong_max', (1, 1))
        #fitter = rti_seq.getMeta('fitter', '')
        #if fitter == '':
        #    log.warning(f"No metadata provided which fitter has to be used, defaulting to '{PolyFitter.__name__}'.")
        #    fitter = PolyFitter.__name__
        #self.initFitter(fitter, {})
        #
        ## Load data
        #self._fitter.loadCoefficients(rti_seq)
    
    @ti.func
    def sample(self, x: ti.i32, y: ti.i32, u: ti.f32, v: ti.f32) -> tib.pixvec:
        rgb = self._coeff[0, y, x]
        #n = 1, 2, 3, 4, 5, 6, 7, 8, 9
        #a = 1, 1, 2, 2, 2, 3, 3, 3, 3
        #b = 0, 1, 0, 1, 2, 0, 1, 2, 3
        
        rgb += self.sampleSum(x, y, u, v, 1, 1)        
        if self._coeff.shape[0] >= 6:
            rgb += self.sampleSum(x, y, u, v, 3, 2)
        if self._coeff.shape[0] >= 10:
            rgb += self.sampleSum(x, y, u, v, 6, 3)
        if self._coeff.shape[0] >= 15:
            rgb += self.sampleSum(x, y, u, v, 10, 4)
        if self._coeff.shape[0] >= 21:
            rgb += self.sampleSum(x, y, u, v, 15, 5)
        if self._coeff.shape[0] >= 28: 
            rgb += self.sampleSum(x, y, u, v, 21, 6)
            
        return tm.max(rgb, 0.0)

    @ti.func
    def sampleSum(self, x, y, u, v, offset, a):
        rgb = self._coeff[offset, y, x] * u**(a)
        for i in range(1, a+1):
            rgb += self._coeff[offset+i, y, x] * u**(a-i) * v**i
        return rgb
