import os
import json 

class Config:
    def __init__(self, path=None):
        self._min=-1
        self._max=-1

        if path is not None:
            self.load(path)
        else:
            self._data = {
                'version': '0.1.0',
                'lights': []
            }

    def addLight(self, id, uv, latlong):
        self._data['lights'].append({'id': id, 'uv': uv, 'latlong': latlong})
        self._min = id if self._min == -1 else min(self._min, id)
        self._max = id if self._max == -1 else max(self._max, id)

    def load(self, path):
        with open(path, "r") as file:
            self._data = json.load(file)
            if not self._data['lights']:
                # Sort it - possibly just sort while saving?
                self._data['lights'] = dict(sorted(self._data['lights'].items())) # TODO: Test it!
                self._min = list(self._data['lights'])[0][id]
                self._max = list(self._data['lights'])[-1][id]

    def save(self, path, name='calibration.json'):
        if not os.path.exists(path):
            os.makedirs(path)
        full_path = os.path.join(path, name)

        with open(full_path, "w") as file:
            json.dump(self._data, file, indent=4) # sort_keys=True


    def get_key_bounds(self):
        return [self._min, self._max]

    def get(self):
        return self._data['lights']

    # TODO: Geht alles nicht:
    
    def get_keys(self):
        return self._data['lights'].keys()

    #def get(self, index):
    #    return list(self._data['lights'].values())[index]
        
    def __getitem__(self, key):
        return self._data['lights'][key]
    
    def __delitem__(self, key):
        del self._data['lights'][key]
    
    def __iter__(self):
        return iter(self._data['lights'].items())

    def __len__(self):
        return len(self._data['lights'])
