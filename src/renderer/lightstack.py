import logging as log

import numpy as np
from numpy.typing import ArrayLike
import math
import cv2 as cv

import taichi as ti
import taichi.math as tm
import taichi.types as tt

from src.imgdata import *
from src.sequence import *
from src.img_op import *

from src.renderer.renderer import *
import src.ti_base as tib
#import src.renderer.ti_stack as tstack


class LightStacker(Renderer):
    name = "Light Stacker"
    def __init__(self):
        self._u_min = self._u_max = self._v_min = self._v_max = None
        
    # Loading, processing etc.
    def load(self, rti_seq: Sequence):
        # Init Taichi field
        res_x, res_y = rti_seq.get(0).resolution()
        self._rti_factors = ti.Vector.field(n=3, dtype=ti.f32, shape=(len(rti_seq), res_y, res_x))
        
        # Copy frames to factors
        arr = np.stack([frame[1].get() for frame in rti_seq], axis=0)
        self._rti_factors.from_numpy(arr)
        
        # Load metadata
        self._u_min, self._v_min = rti_seq.getMeta('latlong_min', (0, 0))
        self._u_max, self._v_max = rti_seq.getMeta('latlong_max', (1, 1))

    
    def get(self) -> Sequence:
        seq = Sequence()
        arr = self._rti_factors.to_numpy()
        
        # Add frames to sequence
        for i in range(self._rti_factors.shape[0]):
            seq.append(ImgBuffer(img=arr[i], domain=ImgDomain.Lin), i)
        
        # Metadata
        seq.setMeta('latlong_min', (self._u_min, self._v_min))
        seq.setMeta('latlong_max', (self._u_max, self._v_max))
        #seq.setMeta('rti_inv', self._mat_inv) # TODO: Really needed?
        return seq
    
    def process(self, img_seq: Sequence, config: Config, settings={}):
        self._sequence = img_seq
        
    
    # Render settings
    def getRenderModes(self) -> list:
        return ("StackLight", "StackHdri")
    
    def getRenderSettings(self, render_mode) -> RenderSettings:
        match render_mode:
            case 0: # StackLight
                return RenderSettings(is_linear=True, needs_coords=True)
            case 1: # StackHdri
                return RenderSettings(is_linear=True, needs_coords=True)
    
    def setCoords(self, u, v):
        self._u = self._u_min + (self._u_max-self._u_min) * u
        self._v = self._v_min + (self._v_max-self._v_min) * v
        self._rot = v

    
    def render(self, render_mode, buffer, hdri=None):
        # Image slices for memory reduction
        slice_length = res_y//8
        sequence = ti.Vector.field(n=3, dtype=ti.f32, shape=(img_count, slice_length, res_x))
        for slice_count in range(res_y//slice_length):
            start = slice_count*slice_length
            end = min((slice_count+1)*slice_length, res_y)            

            match render_mode:
                case 0: # RTILight
                    #trti.sampleLight(buffer, self._rti_factors, self._u, self._v)
                    pass
                case 1: # RTIHdri
                    #self.renderHdri(hdri, self._rot)
                    pass
        

    def renderLight(self, light_pos) -> ImgBuffer:
        # Init Taichi field
        res_x, res_y = (self._rti_factors.shape[2], self._rti_factors.shape[1])
        #pixels = ti.Vector.field(n=3, dtype=ti.f32, shape=(res_y, res_x))
        pixels = ti.ndarray(tt.math.vec3, (res_y, res_x))
        
        u, v = Latlong2UV(light_pos)
        trti.sampleLight(pixels, self._rti_factors, u, v)
        
        return ImgBuffer(img=pixels.to_numpy(), domain=ImgDomain.Lin)
    
    def renderHdri(self, hdri, rotation) -> ImgBuffer:
        # Init Taichi field
        res_x, res_y = (self._rti_factors.shape[2], self._rti_factors.shape[1])
        #pixels = ti.Vector.field(n=3, dtype=ti.f32, shape=(res_y, res_x))
        pixels = ti.ndarray(ti.math.vec3, (res_y, res_x))

        trti.sampleHdri(pixels, self._rti_factors, hdri, rotation)
        
        return ImgBuffer(img=pixels.to_numpy(), domain=ImgDomain.Lin)
    