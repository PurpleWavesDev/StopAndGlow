import os
import json 
import math
import numpy as np
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
                'lights': [], # TODO: Why is this no dict?
                'fitter': {}, # TODO: Not used
            }

    def addLight(self, id, lightpos: LightPosition):
        if lightpos.getChromeball() is not None:
            self._data['lights'].append({'id': id, 'uv': list(lightpos.getChromeball()), 'xyz': list(lightpos.getXYZ())})
        else:
            self._data['lights'].append({'id': id, 'xyz': list(lightpos.getXYZ())})
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
                    light['xyz'] = list(LightPosition.FromMirrorball(light['uv']).getXYZ())
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
    
    def rotate(self, axis, angle):
        m = RotationMatrix(axis, angle)
        for light in self._data['lights']:
            light['xyz'] = m @ light['xyz']
        
    
    def __getitem__(self, id) -> LightPosition:
        return next((LightPosition(light['xyz']) for light in self._data['lights'] if light['id'] == id), None)
    
    def __contains__(self, id):
        return next((True for light in self._data['lights'] if light['id'] == id), False)
    
    def __iter__(self):
        return iter(self.getLights().items())

    def __len__(self) -> int:
        return len(self._data['lights'])
        
    # TODO: Nicht getestet
    def __delitem__(self, id):
        del self._data['lights'][id]
    
    
    ## Stitch functions
    def align(self, new_cals):
        for new_cal in new_cals:
            # Get longitude (Up axis) rotation differences
            diffs = []
            for id, light in self.getLights().items():
                if id in new_cal:
                    diffs.append((new_cal[id].getLL()[1] - light.getLL()[1] + pi_times_2) % pi_times_2)
            # Get median and apply
            rot_correction = np.median(diffs)
            new_cal.rotate([0,0,1], -rot_correction)
            # Get angle difference on Z-Axis
            #diffs = []
            #for id, light in self.getLights().items():
            #    if id in new_cal:
            #        diffs.append(new_cal[id].getXYZ()[2] - light.getXYZ[2])
            ## Median and apply
            #rot_correction = np.median(diffs)
            #new_cal.rotate([0,0,1], rot_correction)
            ## Get angle difference on X-Axis
            #diffs = []
            #for id, light in self.getLights().items():
            #    if id in new_cal:
            #        diffs.append(new_cal[id].getXYZ()[0] - light.getXYZ[0])
            ## Median and apply
            #rot_correction = np.median(diffs)
            #new_cal.rotate([1,0,0], rot_correction)
            
        # new cals should now match with original
        
    def getMerged(self, new_cals):
        """Join all calibratons into a new object"""
        merged_cal = Calibration()
        
        # Join all IDs
        cals = [self, ]+new_cals
        ids = []
        for cal in cals:
            ids += cal.getIds()
        ids = list(set(ids))

        # Weighted merge of coords
        for id in ids:
            xyz = np.array([0,0,0], dtype=float)
            weight = 0.0
            for cal in cals:
                if id in cal.getIds():
                    # TODO: See if vector is totally off (what is the base though?)
                    #print(np.dot(self[id].getXYZ(), cal[id].getXYZ()))
                    # Weighted sum
                    uv = cal[id].getChromeball()
                    cur_weight = 1 - math.sqrt(uv[0]**2 + uv[1]**2) if uv is not None else 1
                    xyz += cal[id].getXYZ() * cur_weight
                    weight += cur_weight
            merged_cal.addLight(id, LightPosition(xyz/weight))
        
        return merged_cal
