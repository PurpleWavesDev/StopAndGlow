from ..utils import *

class LightData:
    def __init__(self, position=None, direction=None, size=0.0, spread=0.0, power=1.0, color=[1.0, 1.0, 1.0]):
        self.position=position
        self.direction=direction
        self.size=size
        self.spread=spread
        self.power=power
        self.color=color

class Scene:
    def __init__(self):
        self._suns = []
        self._points = []
        
    def clear(self):
        self._suns.clear()
        self._points.clear()
    
    def addLight(self, light_data):
        match light_data['type']:
            case 'sun':
                self._suns.append(LightData(direction=light_data['dir'], spread=light_data['spread'], power=light_data['power'], color=light_data['color']))
            case 'point':
                self._points.append(LightData(position=light_data['pos'], size=light_data['size'], power=light_data['power'], color=light_data['color']))
            case 'spot':
                #self._points.append(LightData(position=light_data['pos'], direction=coords, size=light_data['size'], power=light_data['power'], color=light_data['color']))
                pass
            case 'area':
                #self._points.append(LightData(position=light_data['position'], direction=coords, size=light_data['size'], power=light_data['power'], color=light_data['color']))
                pass
    
    def addSun(self, light):
        self._suns.append(light)
    
    def addPoint(self, light):
        self._points.append(light)
    
    def getSunLights(self):
        return self._suns 
        
    def getPointLights(self):
        return self._points
        
    def getSpotLights(self):
        return []
        
    def getAreaLights(self):
        return []
    
    def getHdri(self):
        return None
    