import logging as log

from . import ImgBuffer, Sequence

class CaptureData:
    def __init__(self, path=None):
        self.lights = Sequence()
        self._path = None
        
        if path is not None:
            self.load(path)
    
    def load(self, path):
        self._path = path
        
    def setPath(self, path):
        self._path = path
    
    def save(self, path=None):
        if path is not None:
            self.setPath(path)
        if self._path is not None:
            pass
        else:
            log.error("Can't save CaptureDate without path")
    
    def getData(self, key):
        if not key in self._data:
            self._data[key] = Sequence()
        
        return self._data[key]
    
    def setData(self, key, sequence):
        self._data[key] = sequence