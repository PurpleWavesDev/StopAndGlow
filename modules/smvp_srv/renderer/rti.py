import logging as log
import numpy as np

import taichi as ti
import taichi.math as tm
from .. import ti_base as tib

from ..imgdata import *
from ..sequence import *
from ..config import *
from .renderer import *

from .fitter.pseudoinverse import PseudoinverseFitter
from .fitter.poly import PolyFitter
from .fitter.normal import NormalFitter


class RtiRenderer(Renderer):
    name = "RTI Renderer"
    
    def __init__(self):
        self._fitter = None
        self._normals = None
        self._u_min = self._u_max = self._v_min = self._v_max = None
        
    
    def initFitter(self, fitter, settings):
        """Initializes requested fitter instance"""
        match fitter:
            case PolyFitter.__name__:
                self._fitter = PolyFitter(settings)
        self._normals = NormalFitter()
        
    # Loading, processing etc.
    def load(self, rti_seq: Sequence):
        # Load metadata, get fitter
        self._u_min, self._v_min = rti_seq.getMeta('latlong_min', (0, 0))
        self._u_max, self._v_max = rti_seq.getMeta('latlong_max', (1, 1))
        fitter = rti_seq.getMeta('fitter', '')
        if fitter == '':
            log.warning(f"No metadata provided which fitter has to be used, defaulting to '{PolyFitter.__name__}'.")
            fitter = PolyFitter.__name__
        self.initFitter(fitter, {})
        
        # Load data
        self._fitter.loadCoefficients(rti_seq)
    
    def get(self) -> Sequence:
        if self._fitter:
            seq = self._fitter.getCoefficients()
            seq.setMeta('latlong_min', (self._u_min, self._v_min))
            seq.setMeta('latlong_max', (self._u_max, self._v_max))
            return seq
        return Sequence()
    
    def process(self, img_seq: Sequence, config: Config, settings={}):
        # Validate image sequence 
        if len(img_seq) != len(config):
            log.error(f"Image sequence length ({len(img_seq)}) and number of lights in config ({len(config)}) must match, aborting!")
            return
        # Get dict of light ids with coordinates that are both in the config and image sequence
        #lights = {light['id']: Latlong2UV(light['latlong']) for light in config if light['id'] in img_seq.getKeys()}

        # Settings and initialization
        fitter = settings['fitter'] if 'fitter' in settings else PolyFitter.__name__
        recalc = settings['recalc_inverse'] if 'recalc_inverse' in settings else False        
        self.initFitter(fitter, settings)        
        log.info(f"Generating RTI coefficients with {self._fitter.name}")
        
        # Compute inverse
        self._normals.computeInverse(config)
        self._fitter.computeInverse(config, recalc)
        
        # Compute coefficients
        self._normals.computeCoefficients(img_seq, slices=4)
        self._fitter.computeCoefficients(img_seq, slices=4)
        
        # Save coord bounds
        coord_min, coord_max = config.getCoordBounds()
        self._u_min, self._v_min = Config.NormalizeLatlong(coord_min)
        self._u_max, self._v_max = Config.NormalizeLatlong(coord_max)
    
    # Render settings
    def getRenderModes(self) -> list:
        return ("Light", "HDRI", "Normals")
    
    def getRenderSettings(self, render_mode) -> RenderSettings:
        match render_mode:
            case 0: # Light
                return RenderSettings(is_linear=True, needs_coords=True)
            case 1: # HDRI
                return RenderSettings(is_linear=True, needs_coords=True)
            case 2: # Normals
                return RenderSettings(with_exposure=True)
    
    def setCoords(self, u, v):
        self._u = self._u_min + (self._u_max-self._u_min) * u
        self._v = self._v_min + (self._v_max-self._v_min) * v
        self._rot = v

    # Render!
    def render(self, render_mode, buffer, hdri=None):
        match render_mode:
            case 0: # Light
                self._fitter.renderLight(buffer, (self._u, self._v))
            case 1: # HDRI
                self._fitter.renderHdri(buffer, None, self._rot)
            case 2: # Normals
                self._normals.renderLight(buffer, (0,0))

    def renderLight(self, light_pos) -> ImgBuffer:
        # Init Taichi field
        res_x, res_y = (self._rti_factors.shape[2], self._rti_factors.shape[1])
        #pixels = ti.Vector.field(n=3, dtype=ti.f32, shape=(res_y, res_x))
        pixels = ti.ndarray(tm.vec3, (res_y, res_x))
        
        u, v = Latlong2UV(light_pos)
        trti.sampleLight(pixels, self._rti_factors, u, v)
        
        return ImgBuffer(img=pixels.to_numpy(), domain=ImgDomain.Lin)
    
    def renderHdri(self, hdri, rotation) -> ImgBuffer:
        # Init Taichi field
        res_x, res_y = (self._rti_factors.shape[2], self._rti_factors.shape[1])
        #pixels = ti.Vector.field(n=3, dtype=ti.f32, shape=(res_y, res_x))
        pixels = ti.ndarray(tm.vec3, (res_y, res_x))

        trti.sampleHdri(pixels, self._rti_factors, hdri, rotation)
        
        return ImgBuffer(img=pixels.to_numpy(), domain=ImgDomain.Lin)
    
