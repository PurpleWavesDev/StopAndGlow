import logging as log
import numpy as np
import math
import cv2 as cv
import taichi as ti

from ..data import *
from ..utils import *
from ..hw import Cam
from .viewer import *


class LiveViewer(Viewer):
    name = "live"
    
    def __init__(self, hw):
        self.hw = hw
        self._live_dummy = ImgBuffer(path="./data/live_dummy.JPG")
        self.fps = 24
        self.timer = 0
        self.scaled_array = list()
        self.render_mode = 0
    
    def setResolution(self, resolution):
        pass
    
    def setSequence(self, img_seq: Sequence):
        self.sequence = img_seq
        #image sequence speichern

    # Render settings
    def getModes(self) -> list:
        return ["Live", "Onionskin", "Animation"]

    def setMode(self, mode):
        self.render_mode = mode
        
    def getRenderSettings(self, mode) -> RenderSettings:
        return RenderSettings(as_int=True, req_keypress_events=True, req_inputs=True)

    def keypressEvent(self, event_key):
        if event_key in ['a']: # Left
            self.timer = 0
            self.fps -=1
        elif event_key in ['d']: # Right
            self.timer = 0
            self.fps +=1
        elif event_key in ['w']:
            # Capture photo
            id = self.sequence.getKeyBounds()[1]+1
            self.hw.cam.capturePhoto(id)
            img = self.hw.cam.getImage(id, "", "live")
            self.sequence.append(img, id)
            self.scaled_array.clear()

        elif event_key in ['s']:
            pass

    def inputs(self, window, time_frame):
        pass
        # Poll events from camera, has image been saved?
        #img = self.hw.cam.waitForPhoto(timeout=True, blocking=False)
        #if img is not None:
        #    self.sequence.append(img, self.sequence.getKeyBounds()[1]+1)

    # Rendering
    def render(self, buffer, time_frame):
        match self.render_mode:
            case 0: # Live
                buffer.from_numpy(self.getLiveImage().rescale((buffer.shape[1], buffer.shape[0])).get())

            case 1: # Onionskin
                idx = len(self.sequence)-1
                blended_layer = self.sequence.get(idx).rescale((buffer.shape[1], buffer.shape[0])).get()
               

                for i in range(min(len(self.sequence)-1,3)):
                    img = self.sequence.get(len(self.sequence)-i-2).rescale((buffer.shape[1], buffer.shape[0])).get()
                    if img is not None :
                        blended_layer = cv.addWeighted(blended_layer, 0.65, img,0.25,0)
                    
                    

                blended_layer = cv.addWeighted(self.getLiveImage().rescale((buffer.shape[1], buffer.shape[0])).get(), 0.65, blended_layer,0.25,0)
                buffer.from_numpy(blended_layer)
                
            case 2: # Animation
                    if not self.scaled_array:
                        for id, img in self.sequence:
                            self.scaled_array.append(img.rescale((buffer.shape[1], buffer.shape[0])))
                    idx = int(self.timer*self.fps % len(self.scaled_array))
                    cur_img = self.scaled_array[idx].get()
                    buffer.from_numpy(cur_img)
                    self.timer += time_frame
                    

                    

    def getLiveImage(self):
        try:
            return self.hw.cam.capturePreview()
        except Exception as e:
            return self._live_dummy





