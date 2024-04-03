from enum import Enum
import numpy as np

from ..data import Sequence
from ..hw import Calibration


class Renderer:
    # Loading, processing etc.
    def setBsdf(self, bsdf: BSDF):
        pass

    # Rendering
    def sampleStep(self, samples=10):
        pass
