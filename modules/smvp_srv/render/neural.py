import logging as log
import numpy as np

import taichi as ti
import taichi.math as tm
import taichi.types as tt

from ..utils import ti_base as tib
from ..data import *


@ti.dataclass
class NeuralRtiBsdf:
    def load(self, sequence: Sequence) -> bool:
        return True
    
    @ti.func
    def sample(self, x: ti.i32, y: ti.i32, u: ti.f32, v: ti.f32) -> tib.pixvec:
        rgb = [0, y, x]
            
        return rgb

