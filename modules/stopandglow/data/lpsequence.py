import numpy as np
import logging as log
from collections.abc import Callable
import itertools

from .imgbuffer import *
from .sequence import *
from .calibration import *
from .lightpos import *
from .config import *
from ..utils import imgutils


class LpSequence():
    def __init__(self, seq: Sequence, cal: Calibration):
        # Get dict of light ids with coordinates that are both in the calibration and image sequence
        self._lpframes = dict()
        for id, img in seq:
            if id in cal:
                self._lpframes[id] = (img, cal[id])
            else:
                log.warning(f"Image ID {id} is not available in used calibration")
    
    def filter(self, filter_fn: Callable[[LightPosition], bool]):
        remove_list = []
        
        for id, _, lp in self:
            if filter_fn(id, lp):
                remove_list.append(id)
        
        # Delete items
        log.debug(f"Removing {len(remove_list)} of {len(self._lpframes)} lights")
        for id in remove_list:
            del self._lpframes[id]
    
    def getIds(self) -> list:
        return self._lpframes.keys()
    
    def getImages(self):
        seq = Sequence()
        for id, img, _ in self:
            seq[id] = img
        return seq
    
    def getLights(self): # TODO: Make getLights and Calibration object interchangable
        lights = dict()
        for id, _, lp in self:
            lights[id] = lp
        return lights
    
    def __getitem__(self, id):
        return self._lpframes[id]
    
    def __setitem__(self, id, item):
        self._lpframes[id] = item
    
    def __contains__(self, id):
        return id in self._lpframes[id]

    def __delitem__(self, id):
        del self._lpframes[id]
    
    def __iter__(self):
        return iter([(id, img, lp) for id, (img, lp) in self._lpframes.items()])

    def __len__(self):
        return len(self._lpframes)
    