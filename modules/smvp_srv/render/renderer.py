from enum import Enum
import numpy as np

import taichi as ti
import taichi.math as tm
import taichi.types as tt

from ..utils import ti_base as tib

from ..data import Sequence
from ..hw import Calibration

from .scene import *
from .bsdf import *


@ti.data_oriented
class Renderer:
    def __init__(self, bsdf=BSDF(), resolution=[1920, 1080]):
        self._bsdf = bsdf
        self._scene = Scene()
        self._buffer = ti.field(tib.pixvec)
        self._sample_buffer = ti.field(tib.pixvec)
        ti.root.dense(ti.ij, (resolution[1], resolution[0])).place(self._buffer)
        ti.root.dense(ti.ij, (resolution[1], resolution[0])).place(self._sample_buffer)
        
    def getScene(self):
        return self._scene

    ## Rendering    
    def initRender(self, hdri_samples=0):  
        # Reset sample buffer
        self._sample_buffer.fill(0.0)
        self._hdri_samples = hdri_samples
        self._sample_count = 0
    
    def reset(self):
        self._scene.clear()
    
    def sample(self) -> bool:
        # Reset normal buffer every time (doesn't take long to render this but we could also keep render data for lights separately)
        self._buffer.fill(0.0)
        for lgt in self._scene.getSunLights():
            u, v = 0.0, 0.0
            if len(lgt.direction) == 3:
                u = math.asin(lgt.direction[2]) / pi_by_2
                xy_length = math.sqrt(lgt.direction[0]**2 + lgt.direction[1]**2)
                if xy_length > 0:
                    v = math.acos(lgt.direction[1]/xy_length)/pi_times_2 if lgt.direction[0] < 0 else 1-math.acos(lgt.direction[1]/xy_length)/pi_times_2
            else:
                u, v = lgt.direction
            self.sampleSun(u, v, lgt.angle, lgt.power, lgt.color)
        
        for lgt in self._scene.getPointLights():
            self.samplePoint(lgt.position, lgt.size, lgt.power, lgt.color)
        
        for lgt in self._scene.getSpotLights():
            self.sampleSpot(lgt.position, lgt.direction, lgt.angle/2, lgt.blend, lgt.size, lgt.power, lgt.color)
        
        for lgt in self._scene.getAreaLights():
            self.sampleArea(lgt.position, lgt.direction, lgt.angle, lgt.size, lgt.power, lgt.color)
        
        env_data = self._scene.getHdri()
        if self._sample_count < self._hdri_samples and env_data.power != 0 and env_data.hdri is not None:
            # Sample0
            self.sampleHdri(env_data.hdri, env_data.rotation, env_data.power, 64)
            self._sample_count += 1
        if self._sample_count != 0:
            # Add scaled down to render buffer
            tib.addScaled(self._buffer, self._sample_buffer, 1.0/self._sample_count)
            
        
        return self._hdri_samples == 0 # True if done
    
    def get(self):
        return self._buffer.to_numpy()
    
    def getBuffer(self):
        return self._buffer

    ## Sample kernels
    @ti.kernel
    def sampleSun(self, u: ti.f32, v: ti.f32, angle: ti.f32, power: ti.f32, color: tib.pixvec):
        factor = power * color * 50 # TODO what is this factor?
        
        for y, x in self._buffer:
            self._buffer[y, x] += self._bsdf.sample(x, y, u, v) * factor
    
    @ti.kernel
    def samplePoint(self, pos: tib.pixvec, size: ti.f32, power: ti.f32, color: tib.pixvec):
        factor = power * color
        width = self._buffer.shape[1]
        height_offset = (self._buffer.shape[1]-self._buffer.shape[0]) / 2
        
        for y, x in self._buffer:
            # Calculate vector to pixel: We assume the canvas is 1m wide and centered
            # Canvas is flat for now
            pix2pos = pos - ti.Vector([x/width - 0.5, 0, 0.5-(y+height_offset)/width], dt=ti.f32)
            squared_length = pix2pos[0]**2 + pix2pos[1]**2 + pix2pos[2]**2
            dir = tm.normalize(pix2pos)
            # Calculate angle
            u = tm.asin(dir[2]) / tm.pi + 0.5
            v = 0.5
            xy_length = tm.sqrt(dir[0]**2 + dir[1]**2)
            if xy_length > 0:
                v = tm.acos(tm.clamp(dir[1]/xy_length, -1.0, 1.0))/pi_times_2 if dir[0] < 0 else 1-tm.acos(tm.clamp(dir[1]/xy_length, -1.0, 1.0))/pi_times_2
            self._buffer[y, x] += self._bsdf.sample(x, y, u, v) * factor * 1/squared_length
    
    @ti.kernel
    def sampleSpot(self, pos: tib.pixvec, dir: tib.pixvec, angle: ti.f32, blend: ti.f32, size:ti.f32, power: ti.f32, color: tib.pixvec):
        factor = power * color
        width = self._buffer.shape[1]
        height_offset = (self._buffer.shape[1]-self._buffer.shape[0]) / 2
        
        for y, x in self._buffer:
            # Calculate vector to pixel: We assume the canvas is 1m wide and centered
            # Canvas is flat for now
            pix2pos = pos - ti.Vector([x/width - 0.5, 0, 0.5-(y+height_offset)/width], dt=ti.f32)
            squared_length = pix2pos[0]**2 + pix2pos[1]**2 + pix2pos[2]**2
            # Calculate angles
            ray_dir = tm.normalize(pix2pos)
            ray_angle = tm.acos(tm.dot(ray_dir, dir))
            if ray_angle <= angle:
                # UV coordinates
                u = tm.asin(ray_dir[2]) / tm.pi + 0.5
                v = 0.5
                xy_length = tm.sqrt(ray_dir[0]**2 + ray_dir[1]**2)
                if xy_length > 0:
                    v = tm.acos(tm.clamp(ray_dir[1]/xy_length, -1.0, 1.0))/pi_times_2 if ray_dir[0] < 0 else 1-tm.acos(tm.clamp(ray_dir[1]/xy_length, -1.0, 1.0))/pi_times_2
                
                # Falloff/blend
                if blend > 0:
                    falloff = tm.min(tm.sqrt((angle - ray_angle)/angle / blend), 1)
                    self._buffer[y, x] += self._bsdf.sample(x, y, u, v) * factor * falloff * 1/squared_length
                else:
                    self._buffer[y, x] += self._bsdf.sample(x, y, u, v) * factor  * 1/squared_length
    
    @ti.kernel
    def sampleArea(self, pos: tib.pixvec, dir: tib.pixvec, angle: ti.f32, size: ti.f32, power: ti.f32, color: tib.pixvec): # Size 2D and rectangle/ellipse shape
        factor = power * color
        width = self._buffer.shape[1]
        height_offset = (self._buffer.shape[1]-self._buffer.shape[0]) / 2
        
        for y, x in self._buffer:
            # Calculate vector to pixel: We assume the canvas is 1m wide and centered
            # Canvas is flat for now
            pix2pos = pos - ti.Vector([x/width - 0.5, 0, 0.5-(y+height_offset)/width], dt=ti.f32)
            squared_length = pix2pos[0]**2 + pix2pos[1]**2 + pix2pos[2]**2
            # Calculate angles
            ray_dir = tm.normalize(pix2pos)
            ray_angle = tm.acos(tm.dot(ray_dir, dir))
            if ray_angle <= angle:
                # UV coordinates
                u = tm.asin(ray_dir[2]) / tm.pi + 0.5
                v = 0.5
                xy_length = tm.sqrt(ray_dir[0]**2 + ray_dir[1]**2)
                if xy_length > 0:
                    v = tm.acos(tm.clamp(ray_dir[1]/xy_length, -1.0, 1.0))/pi_times_2 if ray_dir[0] < 0 else 1-tm.acos(tm.clamp(ray_dir[1]/xy_length, -1.0, 1.0))/pi_times_2
                
                self._buffer[y, x] += self._bsdf.sample(x, y, u, v) * factor  * 1/squared_length
    
    @ti.kernel
    def sampleHdri(self, hdri: tib.pixarr, rotation: ti.f32, power: ti.f32, samples: ti.i32):
        for y, x in self._buffer:
            for i in range(samples):
                # TODO Multiple Importance Sampling ?
                # Idea: Sample low count in any direction with blurred HDRI, maybe even with half resolution
                # Rank values and redo sampling around bright areas (gaussian distribution?) -> sampling bright, important values!
                # Problem: Bright parts will be exaggerated, need factor of covered area to scale that down again. For non-gaussian distributions it's probably the spherical angle
                # Far future TODO (especially when we settled on one algorithm): Analytical integration or gradient estimation?
                u = ti.random()*0.65+0.3 # 0 - <1 # TODO Quick fix to mask out lower part of PTM function that shows only rubbish
                v = ti.random()
                #ti.randn(float) # univariate standard normal (Gaussian) distribution of mean 0 and variance 1
                self._sample_buffer[y, x] += self._bsdf.sample(x, y, u, v) * hdri[ti.cast(u*hdri.shape[0], ti.i32), ti.cast((1+v-rotation)%1.0 * hdri.shape[1], ti.i32)] * power / samples
