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
        liveFrame = self.getLiveImage().rescale((buffer.shape[1], buffer.shape[0]))
        match render_mode:
            case 0: # Live
                buffer.from_numpy(liveFrame.get())
            case 1: # Onionskin
                idx = len(self.sequence)-1
                prevImg = self.sequence.get(idx).rescale((buffer.shape[1], buffer.shape[0]))
                blendedLayer = cv.addWeighted(prevImg.get(), 0.65, prevImg.get(),0.25,0)
                idx = idx-1

                for id, img in self.sequence:
                    if img.hasImg :
                        img = img.rescale((buffer.shape[1], buffer.shape[0]))
                        idx = idx-1
                        nextLayer = self.sequence.get(idx).rescale((buffer.shape[1], buffer.shape[0]))
                        blendedLayer = cv.addWeighted(blendedLayer, 0.65, img.get(),0.25,0)

                blendedLayer = cv.addWeighted(liveFrame.get(), 0.65, blendedLayer,0.25,0)
                buffer.from_numpy(blendedLayer)
                

            case 2: # Animation
                for id, img in self.sequence:
                    anim= self.sequence[id].rescale((buffer.shape[1], buffer.shape[0]))
                    buffer.from_numpy(anim.get())

    def getLiveImage(self):
        try:
            return self.hw.cam.capturePreview()
        except:
            return self._live_dummy



