from abc import ABC, abstractmethod

import logging as log
import math
import numpy as np

import taichi as ti
import taichi.math as tm
import taichi.types as tt
from ...utils import *
from ...utils import ti_base as tib

from ...hw.calibration import *
from ...data.sequence import *


class PseudoinverseFitter(ABC):
    name = "Pseudoinverse Fitter"
    
    def __init__(self, settings = {}):
        self._coefficients = self._inverse = None
        self._settings = settings
        self._is_rgb = GetSetting(self._settings, 'rgb', True)
        self._coord_sys = CoordSys[GetSetting(settings, 'coordinate_system', CoordSys.LatLong.name)].value
        self._domain = ImgDomain[GetSetting(settings, 'domain', ImgDomain.Lin.name)].value

    def loadCoefficients(self, coefficient_seq):
        # Load metadata
        coefficient_count = coefficient_seq.getMeta('coefficient_count', 0)
        # Check length of coefficient_count, maybe not load all frames?
        if coefficient_count != 0 and coefficient_count != len(coefficient_seq):
            log.error(f"Coefficient count in metadata ({coefficient_count}) and sequence length ({len(coefficient_seq)}) mismatch!")
        
        # Init coefficient field and copy data
        res_x, res_y = coefficient_seq.get(0).resolution()
        self._coefficients = ti.Vector.field(n=3 if self._is_rgb else 1, dtype=ti.f32, shape=(len(coefficient_seq), res_y, res_x))
        arr = np.stack([frame[1].get() for frame in coefficient_seq], axis=0)
        self._coefficients.from_numpy(arr)
        
        
    def getCoefficients(self) -> Sequence:
        seq = Sequence()
        arr = np.squeeze(self._coefficients.to_numpy())
        
        
        # Add frames to sequence
        coefficient_count = self._coefficients.shape[0]
        if self._is_rgb:
            for i in range(coefficient_count):
                seq.append(ImgBuffer(img=arr[i], domain=self._domain), i)
        else:
            # Three channels in one image
            for i in range(math.ceil(coefficient_count/3)):
                seq.append(ImgBuffer(img=np.moveaxis(arr[i*3:min((i+1)*3, coefficient_count)], 0, -1), domain=self._domain), i) # TODO: Extend to 3 channels when not enough channels are available
        
        # Metadata
        seq.setMeta('fitter', type(self).__name__)
        seq.setMeta('coefficient_count', coefficient_count)
        seq.setMeta('coefficient_count', coefficient_count)
        seq.setMeta('fitter_rgb_channels', self._is_rgb)
        seq.setMeta('coordinate_system', CoordSys(self._coord_sys).name)
        
        return seq
    
    def needsReflectance(self) -> bool:
        return False

    
    @abstractmethod
    def getCoefficientCount(self) -> int:
        """Returns number of coefficients"""
        raise NotImplementedError()
    
    def computeCoefficients(self, img_seq: Sequence, normals=None, slices: int = 1):
        if self._inverse is None:
            log.error("Can't compute coefficients without inverse data, aborting")
            return
        
        coefficient_count = self.getCoefficientCount()
        res_x, res_y = img_seq.get(0).resolution()
        self._coefficients = ti.Vector.field(n=3 if self._is_rgb else 1, dtype=ti.f32, shape=(coefficient_count, res_y, res_x))
        
        # Image slices for memory reduction
        slice_length = res_y // slices
        sequence_buf = ti.Vector.field(n=3 if self._is_rgb else 1, dtype=ti.f32, shape=(len(img_seq), slice_length, res_x))
        for slice_count in range(res_y // slice_length):
            start = slice_count * slice_length
            end = min((slice_count+1) * slice_length, res_y)
            
            # Copy frames to buffer
            for i, id in enumerate(img_seq.getKeys()):
                if self._is_rgb:
                    tib.copyRgbToSequence(sequence_buf, i, img_seq[id].asDomain(self._domain, True).get()[start:end]) # TODO: Match in sRGB?
                else:
                    # TODO: Check if Sequence is single channel already
                    #tib.copyLuminanceToSequence(sequence_buf, i, img_seq[id].asDomain(self._domain, True).RGB2Gray().get()[start:end])
                    tib.copyLuminanceToSequence(sequence_buf, i, img_seq[id].asDomain(self._domain, True).get()[start:end])
           
            # Compute coefficient slice
            computeCoefficientSlice(sequence_buf, self._coefficients, self._inverse, start) 
        del sequence_buf
        

    def computeInverse(self, calibration, recalculate=True):
        # Init array
        light_count = len(calibration)
        coefficient_count = self.getCoefficientCount()
        self._inverse = ti.ndarray(ti.f32, (coefficient_count, light_count))
        
        if not recalculate and calibration.getInverse() is not None:
            # Load from calibration
            self._inverse.from_numpy(calibration.getInverse())
        else:
            # Create array and fill it with light positions
            A = np.zeros((light_count, coefficient_count))
            for i, light in enumerate(calibration.getPositions()):
                self.fillLightMatrix(A[i], light)
                
            # Calculate inverse
            self._inverse.from_numpy(np.linalg.pinv(A).astype(np.float32))
            
    @abstractmethod
    def fillLightMatrix(self, line, lightpos: LightPosition):
        raise NotImplementedError()
    
@ti.kernel
def computeCoefficientSlice(sequence: ti.template(), coefficients: ti.template(), inverse: ti.types.ndarray(dtype=ti.f32, ndim=2), row_offset: ti.i32):
    # Iterate over pixels and factor count
    H, W, C = sequence.shape[1], sequence.shape[2], coefficients.shape[0]
    for y, x, m in ti.ndrange(H, W, C):
        # Matrix multiplication of inverse and sequence pixels
        for n in range(sequence.shape[0]): # n to 200/sequence count, m to 10/factor count
            coefficients[m, y+row_offset, x] += inverse[m, n] * sequence[n, y, x]
