class Scene:
    def __init__(self):
        self._lights = []
        
    def clear(self):
        self._lights.clear()
    
    def addLight(self, light_data):
        print(light_data)
    