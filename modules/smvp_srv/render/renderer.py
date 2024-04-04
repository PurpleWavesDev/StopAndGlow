from enum import Enum
import numpy as np

from ..data import Sequence
from ..hw import Calibration

from .scene import *
from .bsdf import *

@ti.data_oriented
class Renderer:
    def __init__(self):
        self._bsdf = None
        self._scene = Scene()
        
    def setBsdf(self, bsdf: BSDF):
        self._bsdf = bsdf
    
    def getScene(self):
        return self._scene

    ## Rendering
    def initRender(self, buffer=None, sample_count=10):
        # TODO: Make buffer spares according to alpha mask
        if buffer is None:
            if self._buffer is None:
                # Create new buffer
                self._buffer = ti.types.ndarray(dtype=tt.vector(3, ti.f32), ndim=2)
            else:
                # Reset buffer
                pass
        else:
            # Apply buffer
            self._buffer = buffer
    
    def sample(self) -> bool:
        self.sampleSun(0.5, 0.5, 0.0, 1.0, [1.0,1.0,1.0])
        for lgt in self._scene.getSunLights():
            u, v = lgt['direction']
            self.sampleSun(u, v, lgt['angle'], lgt['power'], lgt['color'])
        
        for lgt in self._scene.getPointLights():
            self.samplePoint()
        
        for lgt in self._scene.getSpotLights():
            self.sampleSpot()
        
        for lgt in self._scene.getAreaLights():
            self.sampleArea()
            
        self.sampleHdri()

    ## Sample kernels
    @ti.kernel
    def sampleSun(self, u: ti.f32, v: ti.f32, angle: ti.f32, power: ti.f32, color: tib.pixvec):
        factor = power * color
        
        for y, x in self._buffer:
            self._buffer[y, x] += self._bsdf.sample(u, v) * factor
    
    @ti.kernel
    def samplePoint(self):
        pass
    
    @ti.kernel
    def sampleSpot(self):
        pass
    
    @ti.kernel
    def sampleArea(self):
        pass
    
    @ti.kernel
    def sampleHdri(self):
        pass
