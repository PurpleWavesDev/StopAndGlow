import logging as log

import numpy as np
from numpy.typing import ArrayLike
import math
import cv2 as cv

import taichi as ti
import taichi.math as tm
import taichi.types as tt

from ..utils import ti_base as tib
from ..data import *
from ..hw.calibration import *

from .bsdf import *


@ti.dataclass
class LightstackBsdf:
    name = 'lightstack'
    name_long = 'Lightstack'
    
    def __init__(self):
        pass
    
    def load(self, data: Sequence, calibration: Calibration, settings={}):
        pass
    
    @ti.func
    def sample(self, x: ti.i32, y: ti.i32, n1: ti.f32, n2: ti.f32) -> tib.pixvec:
        return [0, 1, 0]
    
#    # Loading, processing etc.
#    def load(self, sequence: Sequence, calibration: Calibration, settings={}):
#        # Init Taichi fields
#        res_x, res_y = (1024, 512)
#        self._data_id = ti.field(dtype=ti.i16, shape=(res_y, res_x, count))
#        self._data_dist = ti.field(dtype=ti.f32, shape=(res_y, res_x, count))
#
#        # Load metadata
#        self._latlong_min = rti_seq.getMeta('latlong_min', (0, 0))
#        self._latlong_max = rti_seq.getMeta('latlong_max', (1, 1))
#    
#    def sample(self) -> Sequence:
#        seq = Sequence()
#        
#        # Metadata
#        seq.setMeta('latlong_min', self._latlong_min)
#        seq.setMeta('latlong_max', self._latlong_max)
#        
#        return seq
#    
#    def process(self, img_seq: Sequence, calibration: Calibration, settings={'resolution': (1024, 512), 'closest_light_count': 6}):
#        # Create fields and arrays
#        res_x, res_y = settings['resolution'] if 'resolution' in settings else (1024, 512)
#        count = settings['closest_light_count'] if 'closest_light_count' in settings else 6
#        self._data_idx = ti.field(dtype=ti.i32, shape=(res_y, res_x, count))
#        self._data_dist = ti.field(dtype=ti.f32, shape=(res_y, res_x, count))
#        
#        # Light calibration values
#        light_coords = ti.ndarray(dtype=tt.vector(2, ti.f32), shape=(len(calibration)))
#        light_coords.from_numpy(np.array([utils.LatlongRadians(latlong) for latlong in calibration.getCoords()], dtype=np.float32))
#        self._light_ids = calibration.getIds()
#        
#        # Calculate
#        FindClosestLights(self._data_idx, self._data_dist, light_coords)
#        
#        # Get coordinate bounds
#        self._latlong_min, self._latlong_max = calibration.getCoordBounds()
#        self._latlong_min = utils.NormalizeLatlong(self._latlong_min)
#        self._latlong_max = utils.NormalizeLatlong(self._latlong_max)
#        
#        self.setSequence(img_seq)
#    
#    def setSequence(self, img_seq: Sequence):
#        slices = 1
#        self._img_seq = img_seq
#        self._res_x, self._res_y = img_seq.get(0).resolution()
#        
#        # Convert to linear float
#        for id, img in self._img_seq:
#            self._img_seq[id] = img.asDomain(ImgDomain.Lin, as_float=True)
#            
#        # Calculate values for image slicing
#        self._slice_length = self._res_y // slices # TODO
#        self._seq_slice = ti.Vector.field(n=3, dtype=ti.f32, shape=(len(self._img_seq), self._slice_length, self._res_x))
#
#        for i, id in enumerate(self._light_ids): # TODO
#            #if id in self._img_seq:
#            tib.copyFrameToSequence(self._seq_slice, i, self._img_seq[id].get())        
#
#        
#    # Render settings
#    def getRenderModes(self) -> list:
#        return ("SingleLight", "HDRI")
#    
#    def getRenderSettings(self, render_mode) -> RenderSettings:
#        match render_mode:
#            case 0: # SingleLight
#                return RenderSettings(is_linear=True, needs_coords=True)
#            case 1: # HDRI
#                return RenderSettings(is_linear=True, needs_coords=True)
#    
#    def setCoords(self, u, v):
#        self._u = self._latlong_min[0] + (self._latlong_max[0]-self._latlong_min[0]) * u
#        self._v = self._latlong_min[1] + (self._latlong_max[1]-self._latlong_min[1]) * v
#        self._rot = v
#
#    
#    def render(self, render_mode, buffer, hdri=None):
#        # Image slices for memory reduction
#        for slice_count in range(self._res_y // self._slice_length):
#            start = slice_count*self._slice_length
#            end = min((slice_count+1)*self._slice_length, self._res_y)    
#            
#            # Copy frames to buffer
#            #for i, id in enumerate(self._light_ids):
#            #    #if id in self._img_seq:
#            #    tib.copyFrameToSequence(self._seq_slice, i, self._img_seq[id].get()[start:end])        
#
#            match render_mode:
#                case 0: # SingleLight
#                    #trti.sampleLight(buffer, self._rti_factors, self._u, self._v)
#                    sampleLight(buffer, self._seq_slice, start, self._u, self._v, self._data_idx) # self._data_distance, 0.5
#                    pass
#                case 1: # HDRI
#                    #self.renderHdri(hdri, self._rot)
#                    pass
#        
#
#    def renderLight(self, light_pos) -> ImgBuffer:
#        # Init Taichi field
#        pixels = ti.ndarray(tib.pixarr, (self._res_y, self._res_x))
#        
#        u, v = utils.NormalizeLatlong(light_pos)
#        #trti.sampleLight(pixels, self._rti_factors, u, v)
#        
#        return ImgBuffer(img=pixels.to_numpy(), domain=ImgDomain.Lin)
#    
#    def renderHdri(self, hdri, rotation) -> ImgBuffer:
#        # Init Taichi field
#        pixels = ti.ndarray(tib.pixarr, (self._res_y, self._res_x))
#
#        #trti.sampleHdri(pixels, self._rti_factors, hdri, rotation)
#        
#        return ImgBuffer(img=pixels.to_numpy(), domain=ImgDomain.Lin)
#
#
#@ti.kernel
#def sampleLight(pix: tib.pixarr, seq_slice: ti.template(), start: ti.i32, u: ti.f32, v: ti.f32, data_idx: ti.template()):#, data_dist: ti.template(), radius: ti.f32):
#    u_coord = ti.int32(data_idx.shape[0] * u)
#    v_coord = ti.int32(data_idx.shape[1] * v)
#    i = data_idx[u_coord, v_coord, 0]
#    print(u, v, i)
#    for y, x in ti.ndrange(seq_slice.shape[1], seq_slice.shape[2]):
#        # Single light code
#        pix[start+y, x] = seq_slice[i, y, x]
#    
#@ti.kernel
#def FindClosestLights(data_idx: ti.template(), data_dist: ti.template(), light_coords: ti.types.ndarray(dtype=tt.vector(2, ti.f32), ndim=1)):
#    data_count = data_idx.shape[2]
#    light_count = light_coords.shape[0]
#    res_y, res_x = (data_idx.shape[0], data_idx.shape[1])
#    # Reset data
#    for y, x, l in data_idx:
#        data_idx[y,x,l] = ti.i16(-1)
#        data_dist[y,x,l] = tm.pi # Maximum distance possible
#    
#    # Iterate over environment map pixels and calculate latlong coordinates of position
#    for y, x in ti.ndrange(res_y, res_x):
#        latlong = tt.vector(2, ti.f32)([(y/res_y-0.5)*tm.pi, x/res_x*tm.pi*2])
#        
#        # Iterate over lights and calculate distance
#        for i in range(light_count):
#            distance = CalcDistance(latlong, light_coords[i])
#            # Iterate over light seats (?) backwards
#            for l in range(1, data_count+1):
#                idx = data_count-l
#                if data_dist[y, x, idx] > distance:
#                    # Move value to right if current element is not at the end
#                    if l != 1:
#                        data_dist[y, x, idx+1] = data_dist[y, x, idx]
#                        data_idx[y, x, idx+1] = data_idx[y, x, idx]
#                    # Set current value
#                    data_dist[y, x, idx] = distance
#                    data_idx[y, x, idx] = ti.i16(i)
#                else:
#                    # No more bigger distances
#                    break
#            
#    
#    
#@ti.func
#def CalcDistance(latlong1: tt.vector(2, ti.f32), latlong2: tt.vector(2, ti.f32)):
#    dlat = latlong2[0] - latlong1[0]
#    dlon = latlong2[1] - latlong1[1]
#    a = (tm.sin(dlat/2))**2 + tm.cos(latlong1[0]) * tm.cos(latlong2[0]) * (tm.sin(dlon/2))**2
#    return 2 * tm.atan2(tm.sqrt(a), tm.sqrt(1-a)) # c
#    # distance = R * c
#
#