from __future__ import annotations # For type hints
from enum import Enum

from numpy.typing import ArrayLike
import numpy as np
import cv2 as cv
import colour
import colour.models as models

class ImgDomain(Enum):
    sRGB = 0
    Lin = 1
    Rec709 = 2
    Keep = -1

class PixBuf:
    def __init__(self, val=np.array([0.0, 0.0, 0.0]), domain: ImgDomain = ImgDomain.Keep):
        self._val=val
        self._domain=domain
                
    def get(self, trunk_alpha=False) -> ArrayLike:
        if trunk_alpha:
            return self._val[0:3]
        return self._val
    
    def withAlpha(self, alpha=None) -> PixBuf:
        # TODO
        #if alpha is not None:
        #    val = np.dstack((self.get(trunk_alpha=True), alpha))
        #elif not self.hasAlpha():
        #    val = np.dstack((self.get(), np.ones(self._img.shape[0:2], dtype=self._img.dtype)))
        #else:
        val = self._val
        return PixBuf(val=val, domain=self.domain)

    def set(self, val, domain: ImgDomain = ImgDomain.Keep):
        self._val = val
        self._domain = domain
    
    def domain(self):
        return self._domain
    def asDomain(self, domain: ImgDomain, as_float=True) -> PixBuf: # TODO: Untested
        if domain != ImgDomain.Keep and domain != self._domain:
            # Convert to optical/neutral
            img = self.get() if as_float is False else self.asFloat().get()
            match self._domain:
                case ImgDomain.sRGB:
                    if img.dtype == IMAGE_DTYPE_FLOAT and not no_taich:
                            tib.sRGB2Lin(img.copy())
                    else:
                        img = colour.cctf_decoding(img, 'sRGB')
                case ImgDomain.Rec709:
                    img = colour.cctf_decoding(img, 'ITU-R BT.709')
                case _: # Raw/Linear
                    pass
                    
            match domain:
                case ImgDomain.sRGB:
                    if img.dtype == IMAGE_DTYPE_FLOAT and not no_taich:
                        tib.lin2sRGB(img.copy(), 1)
                    else:
                        img = colour.cctf_encoding(img, 'sRGB')
                case ImgDomain.Rec709:
                    img = colour.cctf_encoding(img, 'ITU-R BT.709')
                case _: # Raw/Linear
                    pass

            if img.dtype == 'float64': img = img.astype(IMAGE_DTYPE_FLOAT)
            return PixBuf(img=img, domain=domain)
        return PixBuf(img=self._img, domain=self._domain)
    
    def isFloat(self) -> bool:
        return self._val.dtype == IMAGE_DTYPE_FLOAT
    def asFloat(self) -> PixBuf:
        val = self._val if self.isFloat() else colour.io.convert_bit_depth(self._val, IMAGE_DTYPE_FLOAT) # TODO: Untested
        return PixBuf(val=val, domain=self._domain)
    def isInt(self) -> bool:
        return self._val.dtype == IMAGE_DTYPE_INT
    def asInt(self) -> PixBuf:
        val = self._val if self.isInt() else colour.io.convert_bit_depth(np.clip(self._val, 0, 1), IMAGE_DTYPE_INT) # TODO: Untested
        return PixBuf(val=val, domain=self._domain)
    def channels(self) -> int:
        return self._val.shape[0]
    def hasAlpha(self) -> bool:
        return self.channels() == 4
    def isRgb(self) -> bool:
        return self.channels() >= 3
    def r(self) -> PixBuf:
        return PixBuf(val=self._val[0], domain=self._domain)
    def g(self) -> PixBuf:
        return PixBuf(val=self._val[1], domain=self._domain)
    def b(self) -> PixBuf:
        return PixBuf(val=self._val[2], domain=self._domain)
    def a(self) -> PixBuf:
        return PixBuf(val=self._val[3], domain=self._domain)
    def lum(self) -> PixBuf:
        if self.isRgb():
            return self.RGB2Gray()
        return self
    def RGB2Gray(self) -> PixBuf:
        return PixBuf(val=cv.cvtColor(self._val[0:3].reshape(1,1,3), cv.COLOR_RGB2GRAY).flatten()[0], domain=self._domain)
    def gray2RGB(self) -> PixBuf:
        return PixBuf(val=np.concatenate((self._val, self._val, self._val)), domain=self._domain)
    
    ### Operators ###
    def __getitem__(self) -> PixBuf:
        return self._val
    
    def __setitem__(self, val):
        self._val = val
    
