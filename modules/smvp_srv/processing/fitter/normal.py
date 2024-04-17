from .pseudoinverse import PseudoinverseFitter
from ...hw.calibration import *

import taichi as ti
import taichi.math as tm
import taichi.types as tt
from ...utils import ti_base as tib

class NormalFitter(PseudoinverseFitter):
    name = "Normalmap Fitter"
    
    def __init__(self, settings = {}):
        super().__init__(settings)
        self._settings['rgb'] = False
        # Settings
        #self._scale_positive = settings['scale_to_positive'] if 'scale_to_positive' in settings else True
    
    def getCoefficientCount(self) -> int:
        """Returns number of coefficients"""
        return 3
            
    def fillLightMatrix(self, line, lightpos: LightPosition):
        line = lightpos.getXYZ()
    
