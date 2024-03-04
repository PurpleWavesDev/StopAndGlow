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

class LightWorker(Worker):
    """Writes single light per frame from list"""
    def __init__(self, hw, lights: list[int]|list[dict], mask_frame: list[int]=None, trigger_capture=False, repeat_dmx=0):
        Worker.__init__(self, hw)
        self._lights = lights
        self._single_lights = isinstance(lights[0], int)
        self._i = 0
        self._repeat_dmx = repeat_dmx
        # Picture trigger
        self._trigger = trigger_capture
        # Only record mask frame if list provided
        self._mask_frame = mask_frame
        self._mask_captured = self._mask_frame == None
        
    def work(self) -> bool:
        # First frame is masked frame
        if not self._mask_captured:
            # Set mask frame and write DMX
            light_id = -1
            self.lights.setList(self._mask_frame)
            self._mask_captured = True
        else:
            # Set lights for next frame
            if self._single_lights:
                light_id = self._lights[self._i]
                self.lights.setList([light_id])
            else:
                light_id = self._i
                self.lights.setDict(self._lights[self._i])
            self._i += 1
            
        # Write DMX
        for _ in range(self._repeat_dmx+1):
            self.lights.write()

        # Trigger camera
        if self._trigger:
            self.cam.capturePhoto(light_id)

        # Abort condition
        return self._i < len(self._lights)
    
    
class LightVideoWorker(Worker):
    def __init__(self, hw, lights: list[int]|list[dict], mask_frame: list[int], subframe_count):
        Worker.__init__(self, hw)
        self._lights = lights
        self._single_lights = isinstance(lights[0], int)
        self._mask_frame = mask_frame if mask_frame is not None else lights if self._single_lights else range(512)
        self._subframe_count = subframe_count
        self._i = 0
        
    def init(self):
        # Setup video capture
        self._frame=-2
        self._subframe=0
        self._running = True

    def work(self) -> bool:
        if self._subframe == 0:
            # Set light values on first subframe
            if self._frame == -2:
                # One blackframe
                self.lights.reset()
            elif self._frame == -1:
                # One mask frame
                self.lights.setList(self._mask_frame)
            elif self._frame < len(self._lights):
                if self._single_lights:
                    # Set lights for next frame
                    self.lights.setList([self._lights[self._frame]])
                else:
                    self.lights.setDict(self._lights[self._frame])
            else:
                # Another mask frame
                self.lights.setList(self._mask_frame)
                self._running = False
            
            # Increment frame count
            self._frame += 1
        
        # Write DMX value (every subframe)
        self.lights.write()
        self._subframe = (self._subframe+1) % self._subframe_count

        return self._running


### For more complex animations ###
class LightFnWorker(Worker):
    """For more complex animations, lets callable function set light values each frame"""
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

