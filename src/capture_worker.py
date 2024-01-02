import logging as log
import time

from src.timer import Worker
from src.camera import Cam
from src.lights import Lights

# Todo: Can Capture classes inherit from LightWorker?
class LightWorker(Worker):
    def __init__(self, hw, config=None, range_start=0, range_end=0):
        self.hw=hw
        self.i=0
        if config is not None:
            self.lights=config.getIds()
        else:
            self.lights=range(range_start, range_end)

    def work(self) -> bool:
        # Set values
        light_id = self.lights[self.i]
        self.hw.lights.setList([light_id])
        self.hw.lights.write()

         # Trigger camera
        #self.hw.cam.capture(light_id)

        # Abort condition
        self.i+=1
        return self.i < len(self.lights)
    
class ImageCapture(Worker):
    def __init__(self, hw, config=None, range_start=0, range_end=0):
        self.hw=hw
        self.i=0
        if config is not None:
            self.lights=config.getIds()
        else:
            self.lights=range(range_start, range_end)

    def work(self) -> bool:
        # Set values
        light_id = self.lights[self.i]
        self.hw.lights.setList([light_id])
        self.hw.lights.write()

         # Trigger camera
        self.hw.cam.capture(light_id)

        # Abort condition
        self.i+=1
        return self.i < len(self.lights)
    
class VideoCapture(Worker):
    def __init__(self, hw):
        self.hw=hw
        self.lights=self.hw.config.get()
        self.i=0
        self.blackframe=False

    def work(self) -> bool:
        if not self.blackframe:
            # Set values
            light_id = self.lights[self.i]['id']
            self.hw.lights.setList([light_id])
            self.hw.lights.write()
            self.blackframe=True

            # Trigger camera
            #self.hw.cam.capture(light_id)
            return True

        else:
            self.hw.lights.off()
            self.blackframe=False
            # Abort condition
            self.i+=1
            return self.i < len(self.lights)
