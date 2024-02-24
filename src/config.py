import os
import json 

class Config:
    def __init__(self, path=None):
        self._id_min=-1
        self._id_max=-1
        self._lat_min = self._lat_max = self._long_min = self._long_max = -1

        if path is not None:
            self.load(path)
        else:
            self._data = {
                'version': '0.1.0',
                'lights': []
            }

    def addLight(self, id, uv, latlong):
        self._data['lights'].append({'id': id, 'uv': uv, 'latlong': latlong})
        self._findMinMax(id, latlong)
        
    def load(self, path):
        with open(path, "r") as file:
            self._data = json.load(file)
            for light in self._data['lights']:
                self._findMinMax(light['id'], light['latlong'])

    def save(self, path, name='calibration.json'):
        if not os.path.exists(path):
            os.makedirs(path)
        full_path = os.path.join(path, name)

        with open(full_path, "w") as file:
            json.dump(self._data, file, indent=4)

    def getLights(self):
        return self._data['lights']

    def getByIndex(self, index):
        return self._data['lights'][index]

    def getIdBounds(self):
        return (self._id_min, self._id_max)
    
    def getIds(self):
        return [d['id'] for d in self._data['lights']]
    
    def getCoordBounds(self):
        """Returns minimum and maximum latlong values as (latlong_min, latlong_max)"""
        return ((self._lat_min, self._long_min), (self._lat_max, self._long_max))

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
    def NormalizeLatlong(latlong) -> (float, float):
        """Returns Lat-Long coordinates in the range of 0 to 1"""
        return ((latlong[0]+90) / 180, (latlong[1]+180)%360 / 360)

    
    # Helper
    def _findMinMax(self, id, latlong):
        self._id_min, self._id_max = self._minMax(self._id_min, self._id_max, id)
        self._lat_min, self._lat_max = self._minMax(self._lat_min, self._lat_max, latlong[0])
        self._long_min, self._long_max = self._minMax(self._long_min, self._long_max, latlong[1])
        
    def _minMax(self, cur_val_min, cur_val_max, new_val):
        min_val = new_val if cur_val_min == -1 else min(cur_val_min, new_val)
        max_val = new_val if cur_val_max == -1 else max(cur_val_max, new_val)
        return (min_val, max_val)
