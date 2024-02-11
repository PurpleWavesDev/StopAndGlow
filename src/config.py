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
            if self._data['lights']:
                # List should always be sorted (there is no gurantee though), access ID of first and last element
                self._min = self.getByIndex(0)['id']
                self._max = self.getByIndex(-1)['id']

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
        return [self._min, self._max]
    
    def getIds(self):
        return [d['id'] for d in self._data['lights']]

    def __getitem__(self, key):
        return next((item for item in self._data['lights'] if item["id"] == key), None)

    def __len__(self):
        return len(self._data['lights'])
        
    # TODO: Nicht getestet
    def __delitem__(self, key):
        del self[key]
    
    def __iter__(self):
        return iter(self._data['lights'])
