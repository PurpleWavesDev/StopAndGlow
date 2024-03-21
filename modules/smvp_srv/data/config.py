import os
import json 
import math
from numpy.typing import ArrayLike

class Config:
    def __init__(self, path=None):
        self._changed = False
        if path is not None:
            self.load(path)
        else:
            self._data = {
                'version': '0.2.0',
                'fitter': {}
            }
        
    def load(self, path):
        with open(path, "r") as file:
            self._data = json.load(file)
        if not 'fitter' in self._data:
            self._data['fitter'] = {}
        self._changed = False

    def save(self, path, name='config.json'):
        if not os.path.exists(path):
            os.makedirs(path)
        full_path = os.path.join(path, name)
        with open(full_path, "w") as file:
            json.dump(self._data, file, indent=4)
        self._changed = False
    
