from enum import Enum
import numpy as np

from ..data import Sequence
from ..hw import Calibration

class Processor:
    name = "Processor"
    name_short = "processor"
    
    # Loading, processing etc.
    def get(self) -> Sequence:
        return Sequence()
    def getDefaultSettings() -> dict:
        return {}
    def process(self, img_seq: Sequence, calibration: Calibration, settings=dict()):
        pass
