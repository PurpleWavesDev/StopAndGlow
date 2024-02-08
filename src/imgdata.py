from __future__ import annotations # For type hints
from enum import Enum
from pathlib import Path
import os
import re

import logging as log
from absl import flags

from numpy.typing import ArrayLike
import numpy as np
import cv2 as cv
import imageio
import colour
import colour.models as models
imageio.plugins.freeimage.download()

from src.utils import logging_disabled


IMAGE_DTYPE_FLOAT='float32'
IMAGE_DTYPE_INT='uint8'

class ImgFormat(Enum):
    PNG = 0
    JPG = 1
    EXR = 2
    Keep = -1

class ImgMetadata():
    iso = None
    aperture = None
    exposure = None
    
class ImgDomain(Enum):
    sRGB = 0
    Lin = 1
    Rec709 = 2
    Keep = -1


#class PixBuf:
    #def __init__(self, pix):
    
class ImgBuffer:
    def __init__(self, path=None, img: ArrayLike = None, domain: ImgDomain = ImgDomain.Keep, meta: ImgMetadata = ImgMetadata()):
        self._img=img
        self._domain=domain
        self._format=ImgFormat.Keep
        self._from_file=False
        self._meta = meta
        if self._format == ImgFormat.Keep:
            self.setPath(path)
        else:
            self._path = path
        
    def __del__(self):
        self.unload()
        
    def getPath(self):
        return self._path
        
    def setPath(self, path):
        self._path=path
        if self._path is not None:
            root, ext = os.path.splitext(self._path)
            if ext.lower() == ".jpg" or ext.lower() == ".jpeg":
                self._format=ImgFormat.JPG
            elif ext.lower() == ".png":
                self._format=ImgFormat.PNG
            elif ext.lower() == ".exr":
                self._format=ImgFormat.EXR
    
    def getFormat(self) -> ImgFormat:
        return _format           
    def setFormat(self, format: ImgFormat):
        root, ext = os.path.splitext(self._path)
        if format != ImgFormat.Keep:
            self._format=format
        if self._format != ImgFormat.Keep:
            match format:
                case ImgFormat.PNG:
                    self._path = root+".png"
                case ImgFormat.JPG:
                    self._path = root+".jpg"
                case ImgFormat.EXR:
                    self._path = root+".exr"
        else:
            log.warn("No valid format specified, defaulting to PNG")
            self._format = ImgFormat.PNG
            self._path = root+".png"

    def hasImg(self) -> bool:
        return self._img is not None

    def get(self) -> ArrayLike:
        # Lazy loading
        if self._img is None:
            self.load()
        return self._img

    def set(self, img: ArrayLike, domain: ImgDomain = ImgDomain.Keep, meta: ImgMetadata = ImgMetadata(), overwrite_file=False):
        self._img=img
        self._meta = meta
        if domain != ImgDomain.Keep:
            self._domain = domain
        if overwrite_file:
            self._from_file=False

    def getMeta(self) -> ImgMetadata:
        return self._meta

    def setMeta(self, meta: ImgMetadata):
        self._meta = meta

    def load(self):
        if self._path is not None:
            with logging_disabled():
                # Load images as uint or float according to format and assign domain if not specified
                if self._format != ImgFormat.EXR:# and self._domain != ImgDomain.Lin:
                    self._img = colour.read_image(self._path, bit_depth=IMAGE_DTYPE_INT, method='Imageio')
                    if self._domain == ImgDomain.Keep:
                        self._domain=ImgDomain.sRGB
                else:
                    # TODO: Bug in Imageio? Broken pixel!
                    #self._img = colour.read_image(self._path, bit_depth=IMAGE_DTYPE_FLOAT, method='Imageio')
                    #self._img = np.maximum(self._img, 0)
                    self._img = cv.cvtColor(
                        cv.imread(self._path,  cv.IMREAD_ANYCOLOR | cv.IMREAD_ANYDEPTH),
                        cv.COLOR_BGR2RGB).astype(IMAGE_DTYPE_FLOAT)
                    if self._domain == ImgDomain.Keep:
                        self._domain=ImgDomain.Lin
                        
                self._from_file=True
                log.debug(f"Loaded image {self._path}")
        else:
            log.error("Can't load image without path")
        #original = original[:,:,:3] # Only use red channel
        
    def unload(self, save=False):
        if save and not self._from_file and self._path is not None:
            self.save()
        self._img=None
        
    def save(self, format: ImgFormat = ImgFormat.Keep):
        if self._path is not None and self.get() is not None:
            if format != ImgFormat.Keep:
                # Update path for different format
                self.setFormat(format)
                
            # Create folder
            Path(os.path.split(self._path)[0]).mkdir(parents=True, exist_ok=True)
            self._from_file = True
            
            with logging_disabled():
                match self._format:
                    case ImgFormat.EXR:
                        colour.write_image(self.asFloat().get(), self._path, bit_depth=IMAGE_DTYPE_FLOAT, method='Imageio')
                    case _: # PNG and JPG
                        colour.write_image(self.asDomain(ImgDomain.sRGB).asInt().get(), self._path, bit_depth=IMAGE_DTYPE_INT, method='Imageio')
            #log.debug(f"Saved image {self._path}")
            
        elif self._path is None:
            log.error("Can't save image without path")
    
    def domain(self):
        return self._domain
    def asDomain(self, domain: ImgDomain, as_float=False) -> ImgBuffer:
        if domain != ImgDomain.Keep and domain != self._domain:
            # Convert to optical/neutral
            img = self.get() if as_float is False else self.get().astype(IMAGE_DTYPE_FLOAT)
            match self._domain:
                case ImgDomain.sRGB:
                    img = colour.cctf_decoding(img, 'sRGB')
                case ImgDomain.Rec709:
                    img = colour.cctf_decoding(img, 'ITU-R BT.709')
                case _: # Raw/Linear
                    pass
                    
            match domain:
                case ImgDomain.sRGB:
                    img = colour.cctf_encoding(img, 'sRGB')
                case ImgDomain.Rec709:
                    img = colour.cctf_encoding(img, 'ITU-R BT.709')
                case _: # Raw/Linear
                    pass

            return ImgBuffer(path=self._path, img=img, domain=domain)
        return ImgBuffer(path=self._path, img=self._img, domain=self._domain)
    
    def isFloat(self) -> bool:
        return self.get().dtype == IMAGE_DTYPE_FLOAT
    def asFloat(self) -> ImgBuffer:
        img = self._img if self.isFloat() else colour.io.convert_bit_depth(self._img, IMAGE_DTYPE_FLOAT)
        return ImgBuffer(path=self._path, img=img, domain=self._domain)
    def isInt(self) -> bool:
        return self.get().dtype == IMAGE_DTYPE_INT
    def asInt(self) -> ImgBuffer:
        img = self._img if self.isInt() else colour.io.convert_bit_depth(np.clip(self._img, 0, 1), IMAGE_DTYPE_INT)
        return ImgBuffer(path=self._path, img=img, domain=self._domain)
    def channels(self) -> int:
        if self._img is None:
            return 0
        return self._img.shape[:2]
    def r(self) -> ImgBuffer:
        return ImgBuffer(path=self._path, img=self.get()[...,0], domain=self._domain)
    def g(self) -> ImgBuffer:
        return ImgBuffer(path=self._path, img=self.get()[...,1], domain=self._domain)
    def b(self) -> ImgBuffer:
        return ImgBuffer(path=self._path, img=self.get()[...,2], domain=self._domain)
    def a(self) -> ImgBuffer:
        return ImgBuffer(path=self._path, img=self.get()[...,3], domain=self._domain)
    def RGB2Gray(self) -> ImgBuffer:
        return ImgBuffer(path=self._path, img=cv.cvtColor(self.get(), cv.COLOR_RGB2GRAY), domain=self._domain)
    def gray2RGB(self) -> ImgBuffer:
        return ImgBuffer(path=self._path, img=np.dstack((self.get(),self.get(),self.get())), domain=self._domain)
    
    ### Operators ###
    def __getitem__(self, coord) -> ImgBuffer:
        return ImgBuffer(img=np.array([[self.get()[coord[1]][coord[0]]]]), domain=self._domain)
    
    def __setitem__(self, coord, buf: ImgBuffer):
        val = buf.asDomain(self._domain, self.isFloat())
        self.get()[coord[1]][coord[0]] = val.asInt().get() if self.isInt().get() else val.get()
    
    # Factory for single pixel value
    def FromPix(values, domain: ImgDomain = ImgDomain.sRGB) -> ImgBuffer:
        return ImgBuffer(img=np.array([[values]]).astype(IMAGE_DTYPE_INT)) # TODO: int/float
