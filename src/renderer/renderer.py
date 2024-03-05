from enum import Enum
import numpy as np

from src.sequence import Sequence
from src.config import Config

class RenderSettings:
    def __init__(self, is_linear=False, as_int=False, with_exposure=False, needs_hdri=False, needs_coords=False, req_keypress_events=False, req_inputs=False):
        self.is_linear=is_linear
        self.as_int=as_int
        self.with_exposure=with_exposure
        self.needs_hdri=needs_hdri
        self.needs_coords=needs_coords
        self.req_keypress_events=req_keypress_events
        self.req_inputs=req_inputs

class Renderer:
    name = "Renderer"
    # Loading, processing etc.
    def load(self, img_seq: Sequence):
        pass
    def get(self) -> Sequence:
        return Sequence()
    def process(self, img_seq: Sequence, config: Config, settings=dict()):
        pass
    def setSequence(self, img_seq: Sequence):
        pass

    # Render settings
    def getRenderModes(self) -> list:
        return list()
    def getRenderSettings(self, render_mode) -> RenderSettings:
        return RenderSettings()
    def setCoords(self, u, v):
        pass
    def keypressEvent(self, event_key):
        pass
    def inputs(self, window, time_frame):
        pass
    

    # Rendering
    def render(self, render_mode, buffer, hdri=None):
        pass
