import numpy as np

import taichi as ti
import taichi.math as tm
import taichi.types as tt

from ..utils import ti_base as tib
from ..data import *
from ..hw.calibration import *

@ti.data_oriented
class BSDF:
    def __init__(self):
        self.coord_sys = CoordSys.LatLong.value
    
    def load(self, sequence: Sequence, calibration: Calibration, settings={}) -> bool:
        return True
    
    @ti.func
    def sample(self, x: ti.i32, y: ti.i32, n1: ti.f32, n2: ti.f32) -> tib.pixvec:
        return [0, 0, 0]
