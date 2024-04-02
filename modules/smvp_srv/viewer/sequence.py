import logging as log
import numpy as np
import math
import cv2 as cv
import taichi as ti

from ..data import *
from .viewer import *



class SequenceViewer(Viewer):
    def __init__(self):
        self.render_mode = 0
        self.resolution = (1920, 1080)
        self.sequence = Sequence()
        self.scaled_buf = ImgBuffer()
    
    def setSequence(self, img_seq: Sequence):
        # Set sequence and reset to current render mode
        self.sequence = img_seq
        self.setMode(self.render_mode)

    # Render settings
    def setResolution(self, resolution):
        self.resolution = resolution
    
    def getModes(self) -> list:
        return ["Preview", "Sequence", "Data"]

    def setMode(self, mode):
        self.render_mode = mode
        self.idx = 0
        
        match self.render_mode:
            case 0: # Preview
                self.scaled_buf = self.sequence.getPreview().rescale(self.resolution)
            case 1: # Sequence
                self.scaled_buf = self.sequence[self.idx].rescale(self.resolution)
            case 2: # Data
                # TODO!
                self.scaled_buf = self.sequence[self.idx].rescale(self.resolution)
        
    def getRenderSettings(self, mode) -> RenderSettings:
        return RenderSettings(req_keypress_events=True, with_exposure=True, is_linear=True) # TODO: Linear? Could be metadata of sequence

    def keypressEvent(self, event_key):
        if event_key in ['a']:
            self.idx = self.idx = (len(self.sequence) + self.idx - 1) % len(self.sequence)
        elif event_key in ['d']:
            self.idx = (self.idx + 1) % len(self.sequence)
        
        # Set image depending on render mode
        if self.render_mode == 1:
            self.scaled_buf = self.sequence.get(self.idx)
        if self.render_mode == 2: # TODO!
            self.scaled_buf = self.sequence.get(self.idx)

    # Rendering
    def render(self, buffer, time_frame):
        buffer.from_numpy(self.scaled_buf.get())
