from enum import Enum
import logging as log
import time
import numpy as np

from .hw import *

class EngineModes(Enum):
    Render = 1      # Depends on renderer/bsdf
    Live = 2        # Requires camera link
    Sequence = 3    # Displays sequences and data


class Engine:
    def __init__(self, hw, res=(1920, 1080), mode:EngineModes = None):
        # Init buffers
        self._hw = hw
        self.init(res)
        if mode is not None:
            self.setMode(mode)
        
    def init(self, res, fps=60):
        self._res = res
        
    def setMode(self, mode: EngineModes):
        self._mode = mode
            
    def exit(self):
        self._window = None
    
    def execute(self):
        match self._mode:
            case EngineModes.Render:
                pass
            case EngineModes.Live:
                preview = self._hw.cam.capturePreview()
                scale = max(res[0] / preview.resolution()[0], res[1] / preview.resolution()[1])
                return preview.scale(scale).crop(self._res)
            case EngineModes.Sequence:
                pass
        return ImgBuffer()
            
        if self._window is None:
            self._window = ti.ui.Window("StopLighting Renderer", self._res, show_window=False)
            canvas = window.get_canvas()
            time_last = time.time()

        if not self._window.running:
            return False
        
        
        # Controls
        exposure: np.float32 = 1.0
        #mouse_control = False
        #u: np.float32 = 0.75
        #v: np.float32 = 0.5
        
        pixels = self._buffer_int if False else self._buffer_float
        
        ## Frame times
        #time_cur = time.time()
        #time_frame = time_cur - time_last
        #time_last = time_cur
        
        ### Events ###
        # Key press
        #while window.get_event(ti.ui.PRESS):
        #    # Escape/Quit
        #    if window.event.key in [ti.ui.ESCAPE]: break
        #    # Space for control switch
        #    elif window.event.key in [ti.ui.SPACE]:
        #        mouse_control = not mouse_control
        #    # Arrows for mode changes
        #    elif window.event.key in [ti.ui.RIGHT]:
        #        self.cycleMode()
        #        pixels = buffer_int if self._render_settings.as_int else buffer_float
        #    elif window.event.key in [ti.ui.LEFT]:
        #        self.cycleMode(left=True)
        #        pixels = buffer_int if self._render_settings.as_int else buffer_float
        #    elif self._render_settings.req_keypress_events:
        #        self._renderer.keypressEvent(window.event.key)
        #
        ## Exposure correction
        #if window.is_pressed(ti.ui.UP):
        #    exposure *= 1.0 + (1.0 * time_frame)
        #elif window.is_pressed(ti.ui.DOWN):
        #    exposure /= 1.0 + (1.0 * time_frame)
        
        ## Coordinate inputs
        #if self._render_settings.needs_coords:
        #    if mouse_control:
        #        v, u = window.get_cursor_pos()
        #        u = (u+1) % 1
        #        v = (v+1) % 1
        #    else:
        #        v = (v+time_frame/5) % 1
        #    self._renderer.setCoords(u, v)
        
        # General inputs for renderer
        #if self._render_settings.req_inputs:
        #    self._renderer.inputs(window, time_frame)
        
        ### Rendering ###
        #self._renderer.render(self._mode, pixels, time_frame)
        
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
   
