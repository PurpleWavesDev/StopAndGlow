from enum import Enum
import time

import taichi as ti
import taichi.math as tm
import numpy as np

import src.ti_base as tib

from src.renderer.rti import RtiRenderer


class RenderModules(Enum):
    RTIStandard = 0
    RTITest = 1
    HDRIStack = 2
    
class Viewer:
    def __init__(self, res=(1920, 1080)):
        self._framebuf = ti.field(ti.types.vector(3, ti.f32))
        self._renderer = None
        self._mode = 0
        self._hdris = None
        self.init(res)
        
    def init(self, res):
        self._res = res
        # column-major but with changed x/y coordinates
        ti.root.dense(ti.j, self._res[1]).dense(ti.i, self._res[0]).place(self._framebuf)
        #self._framebuf = ti.VectorType
        
    def setSequences(self, rti_factors = None):
        self._rti_factors = rti_factors

    def setHdris(self, hdris: list):
        self._hdris = hdris
        
    def cycleRenderer(self, new_renderer=None, left=False):
        if new_renderer is not None:
            match renderer:
                case RenderModules.RTIStandard:
                    self._renderer = RtiRenderer()
                    self._renderer.load(self._rti_factors)
                    self._render_settings = self._renderer.getRenderSettings(0)
                    
                case RenderModules.RTITest:
                    pass
        
        self.setMode(0)
                
    def setRenderer(self, renderer):
        self._renderer = renderer
        self.setMode(0)
        
    def cycleMode(self, left=False):
        count = len(self._renderer.getRenderModes)
        if not left:
            self.setMode((self._mode+1) % count)
        else:
            self.setMode((self._mode+count-1) % count)
            
    def setMode(self, mode):
        self._mode = mode
        self._render_settings = self._renderer.getRenderSettings(mode)

    def launch(self):
        if self._renderer == None:
            self.cycleRenderer(RenderModules.RTIStandard)

        window = ti.ui.Window("DomeCtl Viewer", res=self._res, fps_limit=60)
        canvas = window.get_canvas()
        time_last = time.time()
        
        # Controls
        mouse_control = False
        exposure: np.float32 = 1.0
        u: np.float32 = 0.75
        v: np.float32 = 0.5
        
        #pixels = ti.Vector.field(n=3, dtype=ti.f32, shape=(self._res[1], self._res[0]))
        pixels = ti.ndarray(ti.types.vector(3, ti.f32), (self._res[1], self._res[0]))
        while window.running:
            # Frame times
            time_cur = time.time()
            time_frame = time_cur - time_last
            time_last = time_cur
            
            ### Events ###
            # Key press
            while window.get_event(ti.ui.PRESS):
                # Escape/Quit
                if window.event.key in [ti.ui.ESCAPE]: break
                # Space for control switch
                elif window.event.key in [ti.ui.SPACE]:
                    mouse_control = not mouse_control
                # Arrows for mode changes
                elif window.event.key in [ti.ui.RIGHT]:
                    self.cycleMode()
                elif window.event.key in [ti.ui.LEFT]:
                    self.cycleMode(left=True)
            
            # Exposure correction
            if window.is_pressed(ti.ui.UP):
                exposure *= 1.0 + (1.0 * time_frame)
            elif window.is_pressed(ti.ui.DOWN):
                exposure /= 1.0 + (1.0 * time_frame)

            # Coordinate inputs
            if self._render_settings.needs_coords:
                if mouse_control:
                    v, u = window.get_cursor_pos()
                else:
                    v = (v+time_frame/5) % 1
                self._renderer.setCoords(u, v)
            
            ### Rendering ###
            self._renderer.render(self._mode, pixels)
            
            ### Draw GUI ###
            #canvas.
            
            ### Display ###
            if self._render_settings.is_linear:
                tib.lin2sRGB(pixels, exposure)
            elif self._render_settings.with_exposure:
                tib.exposure(pixels, exposure)
            copy_framebuf(pixels, self._framebuf)
            canvas.set_image(self._framebuf)
            window.show()
    
    
    
# Kernels
@ti.kernel
def copy_framebuf(pixel: tib.pixarr, framebuf: ti.template()):
    for y, x in pixel:
        framebuf[x, framebuf.shape[1]-1 -y] = pixel[y, x]
   
