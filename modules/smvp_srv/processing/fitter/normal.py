import numpy as np

import taichi as ti
import taichi.math as tm
import taichi.types as tt

from ...utils import ti_base as tib
from ...data import *
from .pseudoinverse import PseudoinverseFitter


class NormalFitter(PseudoinverseFitter):
    name = "Normalmap Fitter"
    
    def __init__(self, settings = {}):
        super().__init__(settings)
        self._is_rgb = False
        self._coord_sys = CoordSys.XYZ
        # Settings
        #self._scale_positive = settings['scale_to_positive'] if 'scale_to_positive' in settings else True
    
    def getCoefficientCount(self) -> int:
        """Returns number of coefficients"""
        return 3
    
    def needsReflectance(self) -> bool:
        return False
    
    def getFilterFn(self):
        return lambda id, lp: lp.getXYZ()[1] > 0
            
    def fillLightMatrix(self, line, lightpos: LightPosition):
        xyz = lightpos.getXYZ()
        line[:] = [xyz[0], xyz[2], -xyz[1]] # np.dot(vec, xyz)
    
    def getCoefficients(self) -> Sequence:
        normals = np.ascontiguousarray(np.moveaxis(np.squeeze(self._coefficients.to_numpy())[0:3], 0, -1))
        albedo = np.empty_like(normals)
        alpha = np.empty_like(normals)
        val_max = normals.max()
        NormalizeNormals(normals, albedo, alpha, val_max)
        
        seq = Sequence()
        seq.append(ImgBuffer(img=normals, domain=ImgDomain.Lin), 0)
        seq.append(ImgBuffer(img=albedo, domain=ImgDomain.Lin), 1)
        seq.append(ImgBuffer(img=alpha, domain=ImgDomain.Lin), 2)
        seq.setMeta('fitter', type(self).__name__)
        
        return seq


@ti.kernel
def NormalizeNormals(normals: tib.pixarr, albedo: tib.pixarr, alpha: tib.pixarr, val_max: ti.f32):
    for y, x in normals:
        length = tm.length(normals[y, x])
        albedo[y, x] = [length/val_max, length/val_max, length/val_max]
        #normal = normal/2 + 0.5
        if length > val_max * 0.00015:
            # Range from range -1 to 1 -> 0 to 1
            normals[y, x] = normals[y, x] / (2*length) + 0.5
            alpha[y, x] = [1, 1, 1]
        else:
            normals[y, x] = [0.5, 0.5, 1]
            alpha[y, x] = [0, 0, 0]

