import os
import json 
import math
from numpy.typing import ArrayLike
from pathlib import Path

from ..data.lightpos import *

class Calibration:
    def __init__(self, path=None):
        self._id_min=-1
        self._id_max=-1
        self._changed = False

        if path is not None:
            self.load(path)
        else:
            self._data = {
                'version': '0.2.0',
                'lights': [],
                'fitter': {},
            }

    def addLight(self, id, mirror, lightpos: LightPosition):
        self._data['lights'].append({'id': id, 'uv': list(mirror), 'xyz': list(lightpos.getXYZ())})
        self._changed = True
        self._id_max = max(self._id_max, id)
        self._id_min = min(self._id_min, id) if self._id_min != -1 else id
        
    def load(self, path):
        self._id_min=-1
        self._id_max=-1
        self._changed = False
        
        with open(path, "r") as file:
            self._data = json.load(file)
            for light in self._data['lights']:
                if not 'xyz' in light:
                    light['xyz'] = list(LightPosition.MirrorballToCoordinates(light['uv']).getXYZ())
        if not 'fitter' in self._data:
            self._data['fitter'] = {}

    def save(self, path):
        # Create directory
        Path(os.path.dirname(path)).mkdir(parents=True, exist_ok=True)
        
        with open(path, "w") as file:
            json.dump(self._data, file, indent=4)
        self._changed = False

    def setInverse(self, key, inverse: ArrayLike):
        self._data['fitter']['inverse'] = inverse
        self._changed = True
    
    def getInverse(self) -> ArrayLike | None:
        self._data['fitter']['inverse'] if 'inverse' in self._data['fitter'] else None


    def getLights(self) -> dict:
        return {light['id']: LightPosition(light['xyz']) for light in self._data['lights']}
    
    def getIdBounds(self) -> (int, int):
        return (self._id_min, self._id_max)
    
    def getIds(self) -> list[int]:
        return [d['id'] for d in self._data['lights']]
    
    def getPositions(self) -> list[LightPosition]:
        return [LightPosition(light['xyz']) for light in self._data['lights']]
    
    def get(self, index) -> LightPosition:
        return LightPosition(self._data['lights'][index]['xyz'])
    
    def __getitem__(self, id) -> LightPosition:
        return next((LightPosition(light['xyz']) for light in self._data['lights'] if light["id"] == id), None)

    def __len__(self) -> int:
        return len(self._data['lights'])
        
    # TODO: Nicht getestet
    def __delitem__(self, id):
        del self._data['lights'][id]
    
    
    ## Stitch functions
    
    def stitch(self, other_configs):
        add_dict = {}
        for stitch_conf in other_configs:
            # Find lights that have a similar longitude and low latitude
            # TODO This code gets longitude dirfference and adds all lights from the other configs. Not great but better than nothing for now
            long_diff = 0
            for light in self:
                id = light['id']
                if stitch_conf[id] is not None:
                    # This light exists in other calibration as well
                    long_diff += stitch_conf[id]['latlong'][1] - light['latlong'][1]
                    break

            ids = self.getIds()
            for light in stitch_conf:
                if not light['id'] in ids:
                    # This light does not exist, add to calibration
                    light['latlong'][1] = (light['latlong'][1]-long_diff+360) % 360
                    id = light['id']
                    if not id in add_dict:
                        add_dict[id] = (light['uv'], light['latlong'])
                    else:
                        pass
                        #add_dict[id] = ((add_dict[id][0] + light['uv'])/2, (add_dict[id][0] + light['latlong'])/2)
        for light_id, vals in add_dict.items():
            self.addLight(light_id, vals[0], vals[1])

                    #dist = abs(light['uv'][0])-abs(stitch_conf[id]['uv'][0])
                    #dist = light['uv'][0] + stitch_conf[id]['uv'][0]
                    #if abs(dist) < 0.1:
                    #    # The lights with similar u distance on reflection we want to match first
                    #    print(f"Matching light ID {id} with coords {light['latlong']}, {stitch_conf[id]['latlong']}, distance {dist}")
                        
                        