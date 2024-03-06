import os
import json 
import math
from numpy.typing import ArrayLike

class Config:
    def __init__(self, path=None):
        self._id_min=-1
        self._id_max=-1
        self._lat_min = self._lat_max = self._long_min = self._long_max = -1
        self._changed = False

        if path is not None:
            self.load(path)
        else:
            self._data = {
                'version': '0.2.0',
                'lights': [],
                'fitter': {}
            }

    def addLight(self, id, uv, latlong):
        self._data['lights'].append({'id': id, 'uv': uv, 'latlong': latlong})
        self._findMinMax(id, latlong)
        self._changed = True
        
    def load(self, path):
        with open(path, "r") as file:
            self._data = json.load(file)
        for light in self._data['lights']:
            self._findMinMax(light['id'], light['latlong'])
        if not 'fitter' in self._data:
            self._data['fitter'] = {}
        self._changed = False

    def save(self, path, name='calibration.json'):
        if not os.path.exists(path):
            os.makedirs(path)
        full_path = os.path.join(path, name)
        with open(full_path, "w") as file:
            json.dump(self._data, file, indent=4)
        self._changed = False

    def getLights(self):
        return self._data['lights']
    
    def setInverse(self, key, inverse: ArrayLike):
        self._data['fitter']['inverse'] = inverse
        self._changed = True
        
    def getInverse(self) -> ArrayLike | None:
        self._data['fitter']['inverse'] if 'inverse' in self._data['fitter'] else None

    def getByIndex(self, index):
        return self._data['lights'][index]

    def getIdBounds(self):
        return (self._id_min, self._id_max)
    
    def getIds(self):
        return [d['id'] for d in self._data['lights']]
    
    def getCoordBounds(self):
        """Returns minimum and maximum latlong values as (latlong_min, latlong_max)"""
        return ((self._lat_min, self._long_min), (self._lat_max, self._long_max))

    def getCoords(self):
        return [d['latlong'] for d in self._data['lights']]
    
    def __getitem__(self, key):
        return next((item for item in self._data['lights'] if item["id"] == key), None)

    def __len__(self):
        return len(self._data['lights'])
        
    # TODO: Nicht getestet
    def __delitem__(self, key):
        del self._data['lights'][key]
    
    def __iter__(self):
        return iter(self._data['lights'])

    # Statics
    def NormalizeLatlong(latlong) -> [float, float]:
        """Returns Lat-Long coordinates in the range of 0 to 1"""
        return ((latlong[0]+90) / 180, (latlong[1]) / 360)
    
    def LatlongRadians(latlong) -> [float, float]:
        """Returns Lat-Long coordinates as radians in the range of -Pi/2 to Pi/2 Latitude and -Pi to Pi Longitude"""
        return (math.radians(latlong[0]), math.radians(latlong[1]))
    
    # Helper
    def _findMinMax(self, id, latlong):
        self._id_min, self._id_max = self._minMax(self._id_min, self._id_max, id)
        self._lat_min, self._lat_max = self._minMax(self._lat_min, self._lat_max, latlong[0])
        self._long_min, self._long_max = self._minMax(self._long_min, self._long_max, latlong[1])
        
    def _minMax(self, cur_val_min, cur_val_max, new_val):
        min_val = new_val if cur_val_min == -1 else min(cur_val_min, new_val)
        max_val = new_val if cur_val_max == -1 else max(cur_val_max, new_val)
        return (min_val, max_val)

    def stitch(self, other_configs):
        for stitch_conf in other_configs:
            # Find lights that have a similar longitude and low latitude
            for light in self:
                id = light['id']
                if stitch_conf[id] is not None:
                    # This light exists in other config as well
                    #dist = abs(light['uv'][0])-abs(stitch_conf[id]['uv'][0])
                    dist = light['uv'][0] + stitch_conf[id]['uv'][0]
                    if abs(dist) < 0.1:
                        # The lights with similar u distance on reflection we want to match first
                        print(f"Matching light ID {id} with coords {light['latlong']}, {stitch_conf[id]['latlong']}, distance {dist}")
                        
                        