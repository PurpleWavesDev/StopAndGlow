from collections.abc import Callable
from typing import Any
import logging as log
import time

from src.camera import Cam
from src.lights import Lights

SILHOUETTE_LIMITER = 127

class Worker:
    def __init__(self, hw):
        self.cam = hw.cam
        self.lights = hw.lights
        
    def init(self):
        pass
    
    def exit(self):
        pass
        
    def work(self) -> bool:
        return True

class LightListWorker(Worker):
    def __init__(self, hw, lights: list[int], trigger_capture=False):
        Worker.__init__(self, hw)
        self._lightList = lights
        self._i = 0
        self._trigger = trigger_capture
        
    def work(self) -> bool:
        # Set values
        light_id = self._lightList[self._i]
        self.lights.setList([light_id])
        self.lights.write()

        # Trigger camera
        if self._trigger:
            self.cam.capturePhoto(id)

        # Abort condition
        self._i += 1
        return self._i < len(self._lightList)
    
class LightFnWorker(Worker):
    def __init__(self, hw, lights_fn: Callable[[Lights, int, Any], bool], trigger_capture=False, parameter=None):
        Worker.__init__(self, hw)
        self._lights_fn = lights_fn
        self._parameter = parameter
        self._i = 0
        self._trigger = trigger_capture
        
    def work(self) -> bool:
        # Update lights
        ret_val = self._lights_fn(self.lights, self._i, self._parameter)
        self.lights.write()
        
        # Trigger camera
        if self._trigger:
            self.cam.capturePhoto(self._i)

        # Abort condition
        self._i += 1
        return ret_val

    
class VideoListWorker(Worker):
    def __init__(self, hw, lights: list[int], silhouette: list[int]=None, subframe_count=3):
        Worker.__init__(self, hw)
        self._lightList = lights
        self._allOnList = silhouette if silhouette is not None else lights
        self._subframe_count=subframe_count
        
    def init(self):
        # Setup video capture
        self._frame=-2
        self._subframe=0
        self._running = True
    
    def exit(self):
        # Stop video capture
        pass

    def work(self) -> bool:
        if self._subframe == 0:
            # Set light values
            # One blackframe
            if self._frame == -2:
                self.lights.reset()
            elif self._frame == -1:
                # One frame all on/silhouette
                self.lights.setList(self._allOnList, SILHOUETTE_LIMITER)
            elif self._frame < len(self._lightList):
                # Go through IDs
                light_id = self._lightList[self._frame]
                self.lights.setList([light_id])
            else:
                # Another frame all on/silhouette
                self.lights.setList(self._allOnList, int(SILHOUETTE_LIMITER/4))
                self._running = False
            
            # Increment frame count
            # Write DMX value
            self._frame += 1
            self.lights.write()

        self._subframe = (self._subframe+1) % self._subframe_count

        return self._running

class VideoSampleWorker(Worker):
    def __init__(self, hw, light_dict: dict, silhouette: list[int]=None, subframe_count=3):
        Worker.__init__(self, hw)
        self._samples = light_dict
        self._allOnList = silhouette if silhouette is not None else hw.config.getIds()
        self._subframe_count=subframe_count
        
    def init(self):
        # Setup video capture
        self._frame=-2
        self._subframe=0
        self._running = True
    
    def exit(self):
        # Stop video capture
        pass

    def work(self) -> bool:
        if True:#self._subframe == 0:
            # Set light values
            # One blackframe
            if self._frame == -2:
                self.lights.reset()
            elif self._frame == -1:
                # One frame all on/silhouette
                self.lights.setList(self._allOnList, SILHOUETTE_LIMITER)
            elif self._frame < 3:
                # Go through IDs
                self.lights.setLights(self._samples, self._frame)
            else:
                # Another frame all on/silhouette
                self.lights.setList(self._allOnList, int(SILHOUETTE_LIMITER/4))
                self._running = False
            
            # Increment frame count
            # Write DMX value
            self._frame += 1
            self.lights.write()

        #self._subframe = (self._subframe+1) % self._subframe_count

        return self._running
