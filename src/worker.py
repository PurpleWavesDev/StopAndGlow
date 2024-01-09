from collections.abc import Callable
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
        super.lights.setList([light_id])
        super.lights.write()

        # Trigger camera
        if self._trigger:
            super.cam.capturePhoto(id)

        # Abort condition
        self._i += 1
        return self._i < len(self._lightList)
    
class LightFnWorker(Worker):
    def __init__(self, hw, lights_fn: Callable[[Lights, int], bool], trigger_capture=False):
        Worker.__init__(self, hw)
        self._lights_fn = lights_fn
        self._i = 0
        self._trigger = trigger_capture
        
    def work(self) -> bool:
        # Update lights
        ret_val = self._lights_fn(super.lights, i)
        super.lights.write()
        
        # Trigger camera
        if self._trigger:
            super.cam.capturePhoto(id)

        # Abort condition
        self._i += 1
        return ret_val

    
class VideoListWorker(Worker):
    def __init__(self, hw, lights: list[int], silhouette: list[int]=None):
        Worker.__init__(self, hw)
        self._lightList = lights
        self._allOnList = silhouette if silhouette is not None else lights
        
    def init(self):
        # Setup video capture
        self._i=-2
        self._running = True
    
    def exit(self):
        # Stop video capture
        pass

    def work(self) -> bool:
        # Set light values
        # One blackframe
        if self._i == -2:
            super.lights.reset()
        elif self._i == -1:
            # One frame all on/silhouette
            super.lights.setList(self._allOnList)
        elif self._i < len(self._lightList):
            # Go through IDs
            light_id = self._lightList[self._i]
            super.lights.setList([light_id])
        else:
            # Another frame all on/silhouette
            super.lights.setList(self._allOnList, SILHOUETTE_LIMITER)
            self._running = False

        super.lights.write()
        
        # Increment and return
        self._i += 1
        return self._running
