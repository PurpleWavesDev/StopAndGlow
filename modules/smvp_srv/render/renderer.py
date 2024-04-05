from enum import Enum
import numpy as np

from ..data import Sequence
from ..hw import Calibration

from .scene import *
from .bsdf import *

@ti.data_oriented
class Renderer:
    def __init__(self, bsdf=BSDF(), resolution=[1920, 1080]):
        self._bsdf = bsdf
        self._scene = Scene()
        self._buffer = ti.field(tib.pixvec)
        ti.root.dense(ti.ij, (resolution[1], resolution[0])).place(self._buffer)
        
    def getScene(self):
        return self._scene

    ## Rendering    
    def initRender(self, samples=10):  
        # Reset buffer
        self._buffer.fill(0.0)
    
    def reset(self):
        self._scene.clear()
    
    def sample(self) -> bool:
        for lgt in self._scene.getSunLights():
            u, v = lgt.direction
            #u, v = 
            #self.sampleSun(0.5, 0.5, 0.0, 1.0, [1.0,1.0,1.0]) # Test
            self.sampleSun(u, v, lgt.spread, lgt.power, lgt.color)
        
        for lgt in self._scene.getPointLights():
            self.samplePoint()
        
        for lgt in self._scene.getSpotLights():
            self.sampleSpot()
        
        for lgt in self._scene.getAreaLights():
            self.sampleArea()
            
        self.sampleHdri()
    
    def get(self):
        return self._buffer.to_numpy()
    
    def getBuffer(self):
        return self._buffer

    ## Sample kernels
    @ti.kernel
    def sampleSun(self, u: ti.f32, v: ti.f32, angle: ti.f32, power: ti.f32, color: tib.pixvec):
        factor = power * color
        
        for y, x in self._buffer:
            self._buffer[y, x] += self._bsdf.sample(x, y, u, v) * factor
    
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
