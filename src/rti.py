import logging as log
import numpy as np
from numpy.typing import ArrayLike
import math

import cv2 as cv

import taichi as ti
import taichi.math as tm
#from numba import njit, prange, types
#from numba.typed import Dict

from src.imgdata import *
from src.sequence import *
from src.config import *
import src.rti_taichi as rtichi

POL_GRADE_3 = lambda u, v: np.array([1, u, v, u*v, u**2, v**2])
POL_GRADE_4 = lambda u, v: np.concatenate((POL_GRADE_3(u, v), [u**2 * v, v**2 * u, u**3, v**3]))
POL_GRADE_5 = lambda u, v: np.concatenate((POL_GRADE_4(u, v), [u**2 * v**2, u**3 * v, v**3 * u, u**4, v**4]))
POL_GRADE_6 = lambda u, v: np.concatenate((POL_GRADE_5(u, v), [u**3 * v**2, u**2 * v**3, u**4 * v, u * v**4, u**5, v**5]))

def PolGrade(grade, u, v):
    match grade:
        case 3:
            return POL_GRADE_3(u, v)
        case 4:
            return POL_GRADE_4(u, v)
        case 5:
            return POL_GRADE_5(u, v)
        case 6:
            return POL_GRADE_6(u, v)
            
# (1, 3,) 6, 10, 15, 21

class Rti:
    def __init__(self):
        ti.init(arch=ti.gpu, debug=True)
        self._u_min = self._u_max = self._v_min = self._v_max = None
    
    def calculate(self, img_seq: Sequence, config: Config, grade=3):
        # Limit polynom grade and calculate number of factors
        grade = max(3, min(6, grade))
        num_factors = int((grade+1)*grade / 2)
        # Get dict of light ids with coordinates that are both in the config and image sequence
        lights = {light['id']: Rti.Latlong2UV(light['latlong']) for light in config if light['id'] in img_seq.getKeys()}
        log.debug(f"RTI Calculate: {len(lights)} images with light coordinates available in image sequence of length {len(img_seq)}")
        # Get resoultion and image count
        res_x, res_y = img_seq.get(0).resolution()
        img_count = len(lights)
        
        # Generate polynom-matrix
        A = np.zeros((0, num_factors))
        for coord in lights.values():
            u, v = coord
            self._u_min = u if self._u_min is None else min(u, self._u_min)
            self._u_max = u if self._u_max is None else max(u, self._u_max)
            self._v_min = v if self._v_min is None else min(v, self._v_min)
            self._v_max = v if self._v_max is None else max(v, self._v_max)
            A = np.vstack((A, PolGrade(grade, u, v)))
        # Calculate (pseudo)inverse
        mat_inv = np.linalg.pinv(A).astype(np.float32)
        
        # Important fields in full resoultion
        # Field for factors
        self._rti_factors = ti.Vector.field(n=3, dtype=ti.f32, shape=(num_factors, res_y, res_x))
        # Fields for inverse and pixel buffer
        ti_mat_inv = ti.ndarray(dtype=ti.f32, shape=(num_factors, img_count))
        ti_mat_inv.from_numpy(mat_inv)

        # Image slices for memory reduction
        slice_length = int(res_y/8) # TODO Round up?
        sequence = ti.Vector.field(n=3, dtype=ti.f32, shape=(img_count, slice_length, res_x))
        for slice_count in range(int(res_y/slice_length)):
            start = slice_count*slice_length
            end = min((slice_count+1)*slice_length, res_y)
            
            # Copy frames to buffer
            #arr = np.stack([img_seq[id].asDomain(ImgDomain.Lin, as_float=True).get()[start:end] for id in lights.keys()])
            #sequence.from_numpy(arr)
            for i, id in enumerate(lights.keys()):
                rtichi.copyFrame(sequence, i, img_seq[id].asDomain(ImgDomain.Lin, as_float=True).get()[start:end])
            
            # Calculate Factors
            rtichi.calculateFactors(sequence, self._rti_factors, ti_mat_inv, start)
                    
    
    def load(self, rti_seq: Sequence):
        # Init Taichi field
        res_x, res_y = rti_seq.get(0).resolution()
        self._rti_factors = ti.Vector.field(n=3, dtype=ti.f32, shape=(len(rti_seq), res_y, res_x))
        
        # Copy frames to factors
        arr = np.stack([frame[1].get() for frame in rti_seq], axis=0)
        self._rti_factors.from_numpy(arr)
        
        # Load metadata TODO
        self._u_min = self._v_min = 0
        self._u_max = self._v_max = 1
        
    
    def get(self) -> Sequence:
        seq = Sequence()
        arr = self._rti_factors.to_numpy()
        
        for i in range(self._rti_factors.shape[0]):
            seq.append(ImgBuffer(img=arr[i], domain=ImgDomain.Lin), i)
        
        return seq
    
    def sampleLight(self, light_pos) -> ImgBuffer:
        # Init Taichi field
        res_x, res_y = (self._rti_factors.shape[2], self._rti_factors.shape[1])
        pixels = ti.Vector.field(n=3, dtype=ti.f32, shape=(res_y, res_x))
        
        u, v = Rti.Latlong2UV(light_pos)
        rtichi.sampleLight(pixels, self._rti_factors, u, v)
        
        return ImgBuffer(img=pixels.to_numpy(), domain=ImgDomain.Lin)
    
    def sampleHdri(self, hdri, rotation) -> ImgBuffer:
        # Init Taichi field
        res_x, res_y = (self._rti_factors.shape[2], self._rti_factors.shape[1])
        pixels = ti.Vector.field(n=3, dtype=ti.f32, shape=(res_y, res_x))
        
        rtichi.sampleHdri(pixels, self._rti_factors, hdri, rotation)
        
        return ImgBuffer(img=pixels.to_numpy(), domain=ImgDomain.Lin)
    
    def sampleNormals(self) -> ArrayLike:
        # Init Taichi field
        res_x, res_y = (self._rti_factors.shape[2], self._rti_factors.shape[1])
        normals = ti.Vector.field(n=3, dtype=ti.f32, shape=(res_y, res_x))
        
        rtichi.sampleNormals(normals, self._rti_factors)
        
        return ImgBuffer(img=normals.to_numpy(), domain=ImgDomain.Lin)


    def launchViewer(self, hdri=None, scale=1): # TODO: Scale doesnt work
        # Init Taichi field
        res_x, res_y = (int(self._rti_factors.shape[2] * scale), int(self._rti_factors.shape[1] * scale))
        window = ti.ui.Window("RTI Viewer", res=(res_x, res_y), fps_limit=60)
        canvas = window.get_canvas()
        # Fields
        pixels = ti.Vector.field(n=3, dtype=ti.f32, shape=(res_y, res_x))
        img = ti.Vector.field(n=3, dtype=ti.f32, shape=(res_x, res_y))
        if hdri is not None:
            hdri_x, hdri_y = hdri.resolution()
            hdri_ti = ti.Vector.field(n=3, dtype=ti.f32, shape=(hdri_y, hdri_x))
            hdri_ti.from_numpy(hdri.get())
        
        u: ti.f32 = 0.75
        v: ti.f32 = 0.5
        exposure: ti.f32 = 1
        mode = 0
        mode_count = 3
        control_by_mouse = False
        while window.running:
            # Events
            # Arrows, exposure control and mode change
            if window.is_pressed(ti.ui.UP):
                exposure += 0.1
            elif window.is_pressed(ti.ui.DOWN):
                exposure -= 0.1
            if window.get_event(ti.ui.PRESS):
                # Escape/Quit
                if window.event.key in [ti.ui.ESCAPE]: break
                # Space for control switch
                elif window.event.key in [ti.ui.SPACE]:
                    control_by_mouse = not control_by_mouse
                # Mode changes
                elif window.event.key in [ti.ui.RIGHT]:
                    mode = (mode+1) % mode_count
                    if mode == 1 and hdri is None:
                        mode += 1
                elif window.event.key in [ti.ui.LEFT]:
                    mode = (mode+mode_count-1) % mode_count
                    if mode == 1 and hdri is None:
                        mode -= 1
            
            if control_by_mouse:
                v, u = window.get_cursor_pos()
                u = self._u_min + (self._u_max-self._u_min) * u
                v = self._v_min + (self._v_max-self._v_min) * v
            else:
                v = (v+0.01)%1
            
            match mode:
                case 0:
                    rtichi.sampleLight(pixels, self._rti_factors, u, v)
                    rtichi.lin2srgb(pixels, exposure)
                case 1:
                    rtichi.sampleHdri(pixels, self._rti_factors, hdri_ti, v)
                    rtichi.lin2srgb(pixels, exposure)
                case 2:
                    rtichi.sampleNormals(pixels, self._rti_factors)
            rtichi.transpose(pixels, img)
            
            canvas.set_image(img)
            window.show()

        
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
