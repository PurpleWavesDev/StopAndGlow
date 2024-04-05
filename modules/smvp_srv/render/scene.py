from ..utils import *

class LightData:
    def __init__(self, position=None, direction=None, spread=0.0, power=1.0, color=[1.0, 1.0, 1.0]):
        self.position=position
        self.direction=direction
        self.spread=spread
        self.power=power
        self.color=color

class Scene:
    def __init__(self):
        self._suns = []
        
    def clear(self):
        self._suns.clear()
    
    def addLight(self, light_data):
        match light_data['type']:
            case 'sun':
                coords = mutils.NormalizeLatlong(light_data['latlong'])
                self._suns.append(LightData(direction=coords, power=light_data['power'], color=light_data['color']))
            case 'point':
                pass
            case _:
                pass
    
    def addSun(self, sun):
        self._suns.append(sun)
    
    def getSunLights(self):
        return self._suns 
        
    def getPointLights(self):
        return []
        
    def getSpotLights(self):
        return []
        
    def getAreaLights(self):
        return []
    
    def getHdri(self):
        return None
    