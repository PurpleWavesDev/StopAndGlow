import logging as log
import numpy as np

import taichi as ti
import taichi.math as tm

from ..data import *
from ..utils import *
from ..utils import ti_base as tib

from .processor import *
from .lightstack import *
from .fitter import *


class RtiProcessor(Processor):
    name = "rti"
        
    def getDefaultSettings() -> dict:
        return {'coords': 'z_angle', 'rgb': True}
    
    def __init__(self):
        self._fitter = None
        #self._u_min = self._u_max = self._v_min = self._v_max = None
    
    def initFitter(self, fitter, settings):
        """Initializes requested fitter instance"""
        match fitter:
            case PolyFitter.__name__:
                self._fitter = PolyFitter(settings)
            case SHFitter.__name__:
                self._fitter = SHFitter(settings)
            case NormalFitter.__name__:
                self._fitter = NormalFitter(settings)
        
    
    def process(self, img_seq: Sequence, calibration: Calibration, settings={}):
        # Settings and initialization
        fitter = GetSetting(settings, 'fitter', PolyFitter.__name__)
        self.initFitter(fitter, settings)        
        log.info(f"Generating RTI coefficients with {self._fitter.name}")
        
        # Get light position image sequence and filter
        lpseq = LpSequence(img_seq, calibration)
        lpseq.filter(self._fitter.getFilterFn())
        # TODO: Additional filters?
        # TODO: Also duplicate frames maybe?
        
        # Compute inverse
        log.debug(f"Calculate inverse")
        self._fitter.computeInverse(lpseq.getLights())
        
        # Compute coefficients
        log.debug(f"Calculate coefficients")
        if self._fitter.needsReflectance():
            # Use reflectance maps
            # TODO: Where to get good reflectance maps from?!
            #reflectance = Sequence()
            #albedo = img_seq.getDataSequence('shm').get(0).asDomain(ImgDomain.Lin).RGB2Gray().get() # TODO: This is not really an albedo map
            #albedo = np.maximum(albedo, np.full(albedo.shape, 0.0005)) # TODO: What is a good value?
            #for id, img in img_seq:
            #    reflectance[id] = ImgBuffer(img=img.asDomain(ImgDomain.Lin).RGB2Gray().get()/albedo, domain=ImgDomain.Lin)
            
            # Lightstack reflectance (img/avg of front facing images), could be better (but similar to shm0-image)
            lightstack = LightstackProcessor()
            lightstack.process(img_seq, calibration, {'mode': 'average'})
            avg = lightstack.get()
            reflectance = Sequence()
            for id, img, _ in lpseq:
                reflectance.append(ImgBuffer(path=img.getPath(), img=img.get()/avg.get(0).get(), domain=ImgDomain.Lin), id)
            self._fitter.computeCoefficients(reflectance, slices=4)
            
            #img_seq.setDataSequence('average', avg)
            #img_seq.setDataSequence('reflectance', reflectance)
        else:
            # Use normal image sequence
            self._fitter.computeCoefficients(lpseq.getImages(), slices=4)
        
        # Save coord bounds
        #coord_min, coord_max = calibration.getCoordBounds()
        #self._u_min, self._v_min = mutils.NormalizeLatlong(coord_min)
        #self._u_max, self._v_max = mutils.NormalizeLatlong(coord_max)

    
    def get(self) -> Sequence:
        if self._fitter:
            seq = self._fitter.getCoefficients()
            #seq.setMeta('latlong_min', (self._u_min, self._v_min))
            #seq.setMeta('latlong_max', (self._u_max, self._v_max))
            
            # Normalize for normal map
            if isinstance(self._fitter, NormalFitter):
                normal = seq.get(0).get()
                normal = normal/2 + 0.5
                seq.get(0).set(normal)
            return seq
        return Sequence()
    
