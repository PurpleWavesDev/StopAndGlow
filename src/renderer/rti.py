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
from src.config import *
from src.renderer.renderer import *
import src.ti_base as tib
import src.renderer.ti_rti as trti



def TaylorSeries(order, u, v):
    series = np.array([1], dtype=np.float32)
    for n in range(1, order+1):
        for i in range(n+1):
            series = np.append(series, u**(n-i) * v**i)
    return series
def TaylorFactorCount(order):
    # Order:   0, 1, 2,  3,  4
    # Factors: 1, 3, 6, 10, 15, 21
    return (order+1)*(order+2) // 2
    #return (order+1)**2 // 2 + (order+1) // 2
        
def FourierSeries(order, u, v):
    series = np.array([1], dtype=np.float32)
    for n in range(1, order+1):
            for m in range(1, order+1):
                series = np.append(series, (math.cos(n*u)*math.cos(m*v)))
                series = np.append(series, (math.cos(n*u)*math.sin(m*v)))
                series = np.append(series, (math.sin(n*u)*math.cos(m*v)))
                series = np.append(series, (math.sin(n*u)*math.sin(m*v)))
    return series
def FourierFactorCount(order):
    return 4*order*order+1



class RtiRenderer(Renderer):
    name = "RTI Renderer"
    
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
        #seq.setMeta('order', self._order)
        #seq.setMeta('rti_inv', self._mat_inv) # TODO: Really needed?
        return seq
    
    def process(self, img_seq: Sequence, config: Config, settings={'order': 3}):
        # Limit polynom order and calculate number of factors
        order = settings['order'] if 'order' in settings else 3
        order = max(2, min(6, order))
        
        # Get dict of light ids with coordinates that are both in the config and image sequence
        lights = {light['id']: Latlong2UV(light['latlong']) for light in config if light['id'] in img_seq.getKeys()}
        log.debug(f"RTI Calculate: {len(lights)} images with light coordinates available in image sequence of length {len(img_seq)}")
        # Get resoultion and image count
        res_x, res_y = img_seq.get(0).resolution()
        img_count = len(lights)
        
        # Generate polynom-matrix
        num_factors = TaylorFactorCount(order)
        A = np.zeros((0, num_factors))
        # Iterate over lights
        for coord in lights.values():
            u, v = coord
            self._u_min = u if self._u_min is None else min(u, self._u_min)
            self._u_max = u if self._u_max is None else max(u, self._u_max)
            self._v_min = v if self._v_min is None else min(v, self._v_min)
            self._v_max = v if self._v_max is None else max(v, self._v_max)
            A = np.vstack((A, TaylorSeries(order, u, v)))
        # Calculate (pseudo)inverse
        mat_inv = np.linalg.pinv(A).astype(np.float32)
        
        # Important fields in full resoultion
        # Field for factors
        self._rti_factors = ti.Vector.field(n=3, dtype=ti.f32, shape=(num_factors, res_y, res_x))
        # Fields for inverse and pixel buffer
        ti_mat_inv = ti.ndarray(dtype=ti.f32, shape=(num_factors, img_count))
        ti_mat_inv.from_numpy(mat_inv)
        mat_inv = None

        # Image slices for memory reduction
        slice_length = res_y//8
        sequence = ti.Vector.field(n=3, dtype=ti.f32, shape=(img_count, slice_length, res_x))
        for slice_count in range(res_y//slice_length):
            start = slice_count*slice_length
            end = min((slice_count+1)*slice_length, res_y)
            
            # Copy frames to buffer
            for i, id in enumerate(lights.keys()):
                trti.copyFrame(sequence, i, img_seq[id].asDomain(ImgDomain.Lin, as_float=True).get()[start:end])
            
            # Calculate Factors
            trti.calculateFactors(sequence, self._rti_factors, ti_mat_inv, start)

    
    # Render settings
    def getRenderModes(self) -> list:
        return ("RTILight", "RTIHdri", "Normals")
    
    def getRenderSettings(self, render_mode) -> RenderSettings:
        match render_mode:
            case 0: # RTILight
                return RenderSettings(is_linear=True, needs_coords=True)
            case 1: # RTIHdri
                return RenderSettings(is_linear=True, needs_coords=True)
            case 2: # Normals
                return RenderSettings(is_linear=False)
    
    def setCoords(self, u, v):
        self._u = self._u_min + (self._u_max-self._u_min) * u
        self._v = self._v_min + (self._v_max-self._v_min) * v
        self._rot = v

    # Render!
    def render(self, render_mode, buffer, hdri=None):
        match render_mode:
            case 0: # RTILight
                trti.sampleLight(buffer, self._rti_factors, self._u, self._v)
            case 1: # RTIHdri
                #self.renderHdri(hdri, self._rot)
                pass
            case 2: # Normals
                #self.renderNormals()
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
    
    def renderNormals(self) -> ArrayLike:
        # Init Taichi field
        res_x, res_y = (self._rti_factors.shape[2], self._rti_factors.shape[1])
        normals = ti.Vector.field(n=3, dtype=ti.f32, shape=(res_y, res_x))
        
        trti.sampleNormals(normals, self._rti_factors)
        
        return ImgBuffer(img=normals.to_numpy(), domain=ImgDomain.Lin)
        

    # Static functions
def Latlong2UV(latlong) -> [float, float]:
    """Returns Lat-Long coordinates in the range of 0 to 1"""
    return ((latlong[0]+90) / 180, (latlong[1]+180)%360 / 360)

# OpenExr Sample Function    
#import OpenEXR as exr
#
#def read_depth_exr_file(filepath: Path):
#    exrfile = exr.InputFile(filepath.as_posix())
#    raw_bytes = exrfile.channel('B', Imath.PixelType(Imath.PixelType.FLOAT))
#    depth_vector = numpy.frombuffer(raw_bytes, dtype=numpy.float32)
#    height = exrfile.header()['displayWindow'].max.y + 1 - exrfile.header()['displayWindow'].min.y
#    width = exrfile.header()['displayWindow'].max.x + 1 - exrfile.header()['displayWindow'].min.x
#    depth_map = numpy.reshape(depth_vector, (height, width))
#    return depth_map
