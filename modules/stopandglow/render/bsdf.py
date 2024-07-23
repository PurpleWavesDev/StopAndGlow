import numpy as np

import taichi as ti
import taichi.math as tm
import taichi.types as tt

from ..utils import ti_base as tib
from ..data import *

@ti.data_oriented
class BSDF:
    def __init__(self):
        self.coord_sys = CoordSys.LatLong
    
    def configure(self, calibration: Calibration, data_key: str, settings={}):
        self._cal = calibration
        self._data_key = data_key
        self._settings = settings

    def load(self, sequence: Sequence) -> bool:
        return True
    
    @ti.func
    def sample(self, x: ti.i32, y: ti.i32, n1: ti.f32, n2: ti.f32) -> tib.pixvec:
        return [0, 0, 0]
