class Scene:
    def __init__(self):
        self._lights = []
        
    def clear(self):
        self._lights.clear()
    
    def addLight(self, light_data):
        print(light_data)
    
    def getSunLights(self):
        return []   
        
    def getPointLights(self):
        return []
        
    def getSpotLights(self):
        return []
        
    def getAreaLights(self):
        return []
    
    def getHdri(self):
        return None
    