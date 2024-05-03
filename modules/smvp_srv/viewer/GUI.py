from enum import Enum
import logging as log
import time
import math
import taichi as ti
import taichi.math as tm
import numpy as np

from ..utils import ti_base as tib

class ControlMode(Enum):
    Automatic = 0
    Mouse = 1
    Static = 2
    
    def next(self):
        return ControlMode((self.value+1) % len(ControlMode))

class GUI:
    def __init__(self, res=(1920, 1080)):
        self._framebuf = ti.field(ti.types.vector(3, ti.f32))
        self._viewer = None
        self._mode = 0
        self._hdris = None
        self.init(res)
        
    def init(self, res):
        self._res = res
        # column-major but with changed x/y coordinates
        ti.root.dense(ti.j, self._res[1]).dense(ti.i, self._res[0]).place(self._framebuf)
        
    def setSequences(self, image_sequence = None, rti_factors = None):
        if image_sequence is not None:
            self._img_sequence = image_sequence
        if rti_factors is not None:
            self._rti_factors = rti_factors
    
    def setViewer(self, viewer):
        self._viewer = viewer
        self._viewer.setResolution(self._res)
        self.setMode(0)
        
    def cycleMode(self, left=False):
        count = len(self._viewer.getModes())
        if not left:
            self.setMode((self._mode+1) % count)
        else:
            self.setMode((self._mode+count-1) % count)
            
    def setMode(self, mode):
        self._mode = mode
        self._render_settings = self._viewer.getRenderSettings(mode)
        self._viewer.setMode(mode)
        log.info(f"viewer switched to mode {self._viewer.getModes()[mode]}")

    def launch(self):
        if self._viewer == None:
            return

        window = ti.ui.Window(name="StopLighting GUI", res=self._res, fps_limit=60)
        canvas = window.get_canvas()
        time_last = time.time()
        
        # Controls            
        control_mode = ControlMode.Automatic
        exposure: np.float32 = 1.0
        u: np.float32 = 0.5
        v: np.float32 = 0.0
        
        buffer_float = ti.ndarray(ti.types.vector(3, ti.f32), (self._res[1], self._res[0]))
        buffer_int = ti.ndarray(ti.types.vector(3, ti.u8), (self._res[1], self._res[0]))
        pixels = buffer_int if self._render_settings.as_int else buffer_float
        while window.running:
            # Frame times
            time_cur = time.time()
            time_frame = min(time_cur - time_last, 1.0)
            time_last = time_cur
            
            ### Events ###
            # Key press
            while window.get_event(ti.ui.PRESS):
                # Escape/Quit
                if window.event.key in [ti.ui.ESCAPE]: break
                # Space for control switch
                elif window.event.key in [ti.ui.SPACE]:
                    control_mode = control_mode.next()
                # Arrows for mode changes
                elif window.event.key in [ti.ui.RIGHT]:
                    self.cycleMode()
                    pixels = buffer_int if self._render_settings.as_int else buffer_float
                elif window.event.key in [ti.ui.LEFT]:
                    self.cycleMode(left=True)
                    pixels = buffer_int if self._render_settings.as_int else buffer_float
                elif self._render_settings.req_keypress_events:
                    self._viewer.keypressEvent(window.event.key)
            
            # Exposure correction
            if window.is_pressed(ti.ui.UP):
                exposure *= 1.0 + (1.0 * time_frame)
            elif window.is_pressed(ti.ui.DOWN):
                exposure /= 1.0 + (1.0 * time_frame)

            # Coordinate inputs
            if self._render_settings.needs_coords:
                match control_mode:
                    case ControlMode.Automatic:
                        v = (v+time_frame/3)
                        v -= math.floor(abs(v)) * 2 # Reset to -1 for values above 1
                    case ControlMode.Mouse:
                        v, u = window.get_cursor_pos()
                        u = u*2 - 1
                        v = v*2 - 1
                self._viewer.setCoords(u, v)
            
            # General inputs for viewer
            if self._render_settings.req_inputs:
                self._viewer.inputs(window, time_frame)
            
            ### Rendering ###
            self._viewer.render(pixels, time_frame)
            
            ### Draw GUI ###
            #canvas.
            
            ### Display ###
            if self._render_settings.is_linear:
                tib.lin2sRGB(pixels, exposure)
            elif self._render_settings.with_exposure:
                tib.exposure(pixels, exposure)
            copy_framebuf8(pixels, self._framebuf) if self._render_settings.as_int else copy_framebuf(pixels, self._framebuf)
            canvas.set_image(self._framebuf)
            window.show()
    
    
    
# Kernels
@ti.kernel
def copy_framebuf(pixel: tib.pixarr, framebuf: ti.template()):
    for y, x in pixel:
        framebuf[x, framebuf.shape[1]-1 -y] = pixel[y, x]
   
# Kernels
@ti.kernel
def copy_framebuf8(pixel: tib.pixarr8, framebuf: ti.template()):
    for y, x in pixel:
        framebuf[x, framebuf.shape[1]-1 -y] = pixel[y, x]/255
   
