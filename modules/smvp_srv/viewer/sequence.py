import logging as log
import numpy as np
import math
import cv2 as cv
import taichi as ti

from ..data import *
from .viewer import *


class SequenceViewer(Viewer):
    name = "sequence"
    
    def __init__(self):
        self.render_mode = 0
        self.resolution = (1920, 1080)
        self.sequence = Sequence()
        self.data_keys = []
        self.scaled_buf = ImgBuffer()
    
    def setSequence(self, img_seq: Sequence):
        # Set sequence and reset to current render mode
        self.sequence = img_seq
        self.data_keys = self.sequence.getDataKeys()
        self.setMode(self.render_mode)

    # Render settings
    def setResolution(self, resolution):
        self.resolution = resolution
    
    def getModes(self) -> list:
        return ["Preview", "Sequence", "Data"]

    def setMode(self, mode):
        self.render_mode = mode
        self.idx = 0
        self.data_idx = 0
        
        match self.render_mode:
            case 0: # Preview
                self.scaled_buf = self.sequence.getPreview().rescale(self.resolution)
            case 1: # Sequence
                self.scaled_buf = self.sequence.get(self.idx).rescale(self.resolution)
            case 2: # Data
                # TODO: What if sequence is empty or no data sequences are available?
                if self.data_keys and len(self.sequence.getDataSequence(self.data_keys[self.data_idx])) > 0:
                    self.scaled_buf = self.sequence.getDataSequence(self.data_keys[self.data_idx]).get(self.idx).rescale(self.resolution)
        
    def getRenderSettings(self, mode) -> RenderSettings:
        return RenderSettings(req_keypress_events=True if mode > 0 else False, with_exposure=True, is_linear=True) # TODO: Linear? Could be metadata of sequence

    def keypressEvent(self, event_key):
        seq_length = len(self.sequence) if self.render_mode == 1 else len(self.sequence.getDataSequence(self.data_keys[self.data_idx]))
        data_length = len(self.data_keys)
        
        if event_key in ['a']:
            self.idx = self.idx = (seq_length + self.idx - 1) % seq_length
        elif event_key in ['d']:
            self.idx = (self.idx + 1) % seq_length
        elif self.render_mode == 2 and data_length > 0:
            if event_key in ['s']:
                self.data_idx = self.data_idx = (data_length + self.data_idx - 1) % data_length
                self.idx = 0
            elif event_key in ['w']:
                self.data_idx = (self.data_idx + 1) % data_length
                self.idx = 0
        
        # Set image depending on render mode
        if self.render_mode == 1:
            self.scaled_buf = self.sequence.get(self.idx).rescale(self.resolution)
        elif self.render_mode == 2 and data_length > 0:
            self.scaled_buf = self.sequence.getDataSequence(self.data_keys[self.data_idx]).get(self.idx).rescale(self.resolution)

    # Rendering
    def render(self, buffer, time_frame):
        buffer.from_numpy(self.scaled_buf.get())
