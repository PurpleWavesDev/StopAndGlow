import logging as log
import numpy as np
import math
import cv2 as cv
import taichi as ti

from src.imgdata import *
from src.sequence import Sequence
from src.img_op import *
from src.config import Config
from src.utils import logging_disabled
from src.mathutils import *
from src.renderer.renderer import *
from src.camera import *



class LiveView(Renderer):
    def __init__(self, hw):
        self.hw = hw
        self._live_dummy = ImgBuffer(path="../HdM_BA/data/live_dummy.JPG")
        self.fps = 24
        self.timer = 0
        
    def load(self, img_seq: Sequence):
        pass
    
    def get(self) -> Sequence:
        return Sequence()
                
    def setSequence(self, img_seq: Sequence):
        self.sequence = img_seq
        #image sequence speichern

    # Render settings
    def getRenderModes(self) -> list:
        return ["Live", "Onionskin", "Animation"]

    def getRenderSettings(self, render_mode) -> RenderSettings:
        return RenderSettings(as_int=True, req_keypress_events=True)

    def keypressEvent(self, event_key):
        if event_key in ['a']: # Left
            self.timer = 0
            self.fps *= 2
        elif event_key in ['d']: # Right
            self.timer = 0
            self.fps = self.fps // 2

        elif event_key in ['w']:
            pass
        elif event_key in ['s']:
            pass

    # Rendering
    def render(self, render_mode, buffer, cur_time, hdri=None):
        live_frame = self.getLiveImage().rescale((buffer.shape[1], buffer.shape[0]))
        match render_mode:
            case 0: # Live
                buffer.from_numpy(live_frame.get())
            case 1: # Onionskin
                idx = len(self.sequence)-1
                prev_img = self.sequence.get(idx).rescale((buffer.shape[1], buffer.shape[0]))
                blended_layer = cv.addWeighted(prev_img.get(), 0.65, prev_img.get(),0.25,0)
                idx = idx-1

                for id, img in self.sequence:
                    if img.hasImg :
                        img = img.rescale((buffer.shape[1], buffer.shape[0]))
                        idx = idx-1
                        nextLayer = self.sequence.get(idx).rescale((buffer.shape[1], buffer.shape[0]))
                        blended_layer = cv.addWeighted(blended_layer, 0.65, img.get(),0.25,0)

                blended_layer = cv.addWeighted(live_frame.get(), 0.65, blended_layer,0.25,0)
                buffer.from_numpy(blended_layer)
                
            case 2: # Animation
                    idx = int(self.timer*self.fps % len(self.sequence))
                    cur_img = self.sequence.get(idx).rescale((buffer.shape[1], buffer.shape[0])).get()
                    buffer.from_numpy(cur_img)
                    self.timer += cur_time
                    

                    

    def getLiveImage(self):
        try:
            return self.hw.cam.capturePreview()
        except:
            return self._live_dummy





