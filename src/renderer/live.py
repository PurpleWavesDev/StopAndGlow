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
            self._view_idx = (len(self._sequence)+self._view_idx-1) % len(self._sequence)
        elif event_key in ['d']: # Right
            self._view_idx = (self._view_idx+1) % len(self._sequence)
        elif event_key in ['w']:
            pass
        elif event_key in ['s']:
            pass

    # Rendering
    def render(self, render_mode, buffer, hdri=None):
        match render_mode:
            case 1: # Live
                self.getLiveImage().rescale((buffer.shape[1], buffer.shape[0]))
                buffer.from_numpy(frame.get())
            case 0: # Onionskin
             self.sequence.get(5)         
                
            case 2: # Animation
                for id, img in self.sequence:
                    self.sequence[id]

    def getLiveImage(self):
        try:
            return self.hw.cam.capturePreview()
        except:
            return self._live_dummy



