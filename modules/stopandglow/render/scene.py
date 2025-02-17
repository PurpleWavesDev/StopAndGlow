from ..data.imgbuffer import *
from ..utils import *

from ..utils import ti_base as tib
import taichi as ti
import taichi.types as tt

class LightData:
    def __init__(self, position=None, direction=None, angle=0.0, blend=0.0, size=0.0, power=1.0, color=[1.0, 1.0, 1.0]):
        self.position=position
        self.direction=direction
        self.angle=angle
        self.blend=blend
        self.size=size
        self.power=power
        self.color=color

class EnvironmentData:
    def __init__(self, hdri: tib.pixarr, rotation=0.0, power=1.0):
       self.hdri=hdri
       self.rotation=rotation 
       self.power=power

class Scene:
    def __init__(self):
        self._suns = []
        self._points = []
        self._spots = []
        self._areas = []
        self._hdri = EnvironmentData(None)
        
    def clear(self):
        self._suns.clear()
        self._points.clear()
        self._spots.clear()
        self._areas.clear()
    
    def clearHdri(self):
        self._hdri = EnvironmentData(None)
    
    def addLight(self, light_data):
        match light_data['type']:
            case 'sun':
                self._suns.append(LightData(direction=light_data['dir'], angle=light_data['angle'], power=light_data['power'], color=light_data['color']))
            case 'point':
                self._points.append(LightData(position=light_data['pos'], size=light_data['size'], power=light_data['power'], color=light_data['color']))
            case 'spot':
                self._spots.append(LightData(position=light_data['pos'], direction=light_data['dir'], angle=light_data['angle'], blend=light_data['blend'],\
                    size=light_data['size'], power=light_data['power'], color=light_data['color']))
            case 'area':
                self._spots.append(LightData(position=light_data['pos'], direction=light_data['dir'], angle=light_data['angle'], size=light_data['size'], power=light_data['power'], color=light_data['color']))
                
    
    def addSun(self, light):
        self._suns.append(light)
    
    def addPoint(self, light):
        self._points.append(light)
        
    def addSpot(self, light):
        self._spots.append(light)
    
    def addArea(self, light):
        self._areas.append(light)
    
    def setHdri(self, hdri: ImgBuffer, rotation=0.0, power=1.0):
        hdri_buf = ti.ndarray(tib.pixvec, hdri.shape())
        hdri_buf.from_numpy(hdri.asDomain(ImgDomain.Lin).get())
        self._hdri = EnvironmentData(hdri_buf, rotation, power)
    
    def setHdriData(self, rotation=None, power=None):
        if rotation is not None:
            self._hdri.rotation = rotation
        if power is not None:
            self._hdri.power = power
    
    def getSunLights(self):
        return self._suns 
        
    def getPointLights(self):
        return self._points
        
    def getSpotLights(self):
        return self._spots
        
    def getAreaLights(self):
        return self._areas
    
    def getHdri(self):
        return self._hdri
    