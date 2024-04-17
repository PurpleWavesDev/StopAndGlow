import logging as log
import numpy as np

import taichi as ti
import taichi.math as tm

from ..data import *
from ..utils import *
from ..utils import ti_base as tib

from .processor import *
from .fitter import *


class RtiProcessor(Processor):
    name = "rti"
        
    def getDefaultSettings() -> dict:
        return {'order': 3}
    
    def __init__(self):
        self._fitter = None
        self._u_min = self._u_max = self._v_min = self._v_max = None
    
    def initFitter(self, fitter, settings):
        """Initializes requested fitter instance"""
        match fitter:
            case PolyFitter.__name__:
                self._fitter = PolyFitter(settings)
            case NormalFitter.__name__:
                self._fitter = NormalFitter(settings)
        
    
    def process(self, img_seq: Sequence, calibration: Calibration, settings={}):
        # Validate image sequence 
        if len(img_seq) != len(calibration):
            log.error(f"Image sequence length ({len(img_seq)}) and number of lights in calibration ({len(calibration)}) must match, aborting!")
            return
        # Get dict of light ids with coordinates that are both in the calibration and image sequence
        #lights = {light['id']: Latlong2UV(light['latlong']) for light in calibration if light['id'] in img_seq.getKeys()}

        # Settings and initialization
        fitter = GetSetting(settings, 'fitter', PolyFitter.__name__)
        recalc = GetSetting(settings, 'recalc_inverse', False)        
        self.initFitter(fitter, settings)        
        log.info(f"Generating RTI coefficients with {self._fitter.name}")
        
        # Compute inverse
        self._fitter.computeInverse(calibration, recalc)
        
        # Compute coefficients
        self._fitter.computeCoefficients(img_seq, slices=4)
        
        # Save coord bounds
        #coord_min, coord_max = calibration.getCoordBounds()
        #self._u_min, self._v_min = mutils.NormalizeLatlong(coord_min)
        #self._u_max, self._v_max = mutils.NormalizeLatlong(coord_max)

    
    def get(self) -> Sequence:
        if self._fitter:
            seq = self._fitter.getCoefficients()
            #seq.setMeta('latlong_min', (self._u_min, self._v_min))
            #seq.setMeta('latlong_max', (self._u_max, self._v_max))
            return seq
        return Sequence()
    
