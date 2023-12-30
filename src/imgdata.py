from enum import Enum
import os
import re

import logging as log
from src.utils import logging_disabled

import numpy as np
import cv2 as cv
import colour
import colour.models as models
import imageio
imageio.plugins.freeimage.download()

IMAGE_DTYPE_FLOAT='float16'
IMAGE_DTYPE_INT='uint8'


class ImgFormat(Enum):
    PNG = 0
    JPG = 1
    EXR = 2
    Keep = -1
    
class ImgDomain(Enum):
    sRGB = 0
    Lin = 1
    Rec709 = 2
    Keep = -1


class ImgBuffer:
    def __init__(self, path=None, img=None, domain=ImgDomain.Keep):
        self._img=img
        self._domain=domain
        self._format=ImgFormat.Keep
        self._from_file=False
        self.setPath(path)
        
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
                
    def setFormat(self, format):
        if img_format != ImgFormat.Keep and img_format != self._format:
            root, ext = os.path.splitext(self._path)
            match self._format:
                case ImgFormat.PNG:
                    self._path = root+".png"
                case ImgFormat.JPG:
                    self._path = root+".jpg"
                case ImgFormat.EXR:
                    self._path = root+".exr"
                        
            self._path=self._path #TODO
            self._format=img_format
        
    def get(self):
        # Lazy loading
        if self._img is None:
            self.load()
        return self._img

    def set(self, img, overwrite_file=False):
        self._img=img
        if overwrite_file:
            self._from_file=False

    def load(self):
        if self._path is not None:
            with logging_disabled():
                # Load images as uint or float according to format and assign domain if not specified
                if self._format != ImgFormat.EXR:# and self._domain != ImgDomain.Lin:
                    self._img = colour.read_image(self._path, bit_depth=IMAGE_DTYPE_INT, method='Imageio')
                    if self._domain == ImgDomain.Keep:
                        self._domain=ImgDomain.sRGB
                else:
                    self._img = colour.read_image(self._path, bit_depth=IMAGE_DTYPE_FLOAT, method='Imageio')
                    if self._domain == ImgDomain.Keep:
                        self._domain=ImgDomain.Lin
                        
                self._from_file=True
                log.debug(f"Loaded image {self._path}")
        else:
            log.error("Can't load image without path")
        #original = original[:,:,:3] # Only use red channel
        
    def unload(self):
        if not self._from_file and self._path is not None:
            self.save()
        self._img=None
        
    def save(self, img_format=ImgFormat.Keep):
        if self._path is not None and self._img is not None:
            # Check if different format is requested and update path
            self.setFormat(img_format)
                
            match self._format:
                case ImgFormat.EXR:
                    colour.write_image(self._img, self._path, 'float32', method='Imageio')
                case _: # PNG and JPG
                    colour.write_image(self._img, self._path, 'uint8', method='Imageio')
            log.debug(f"Saved image {self._path}")
            
        else:
            log.error("Can't save image without path")
        
    def convert(self, domain, as_float=False):
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
        
    def asFloat(self):
        return ImgBuffer(path=self._path, img=colour.io.convert_bit_depth(self.get(), IMAGE_DTYPE_FLOAT), domain=self._domain)
    def asInt(self):
        return ImgBuffer(path=self._path, img=colour.io.convert_bit_depth(self.get(), IMAGE_DTYPE_INT), domain=self._domain)
    def r(self):
        return ImgBuffer(path=self._path, img=self.get()[...,0], domain=self._domain)
    def g(self):
        return ImgBuffer(path=self._path, img=self.get()[...,1], domain=self._domain)
    def b(self):
        return ImgBuffer(path=self._path, img=self.get()[...,2], domain=self._domain)
    def a(self):
        return ImgBuffer(path=self._path, img=self.get()[...,3], domain=self._domain)
    def RGB2Gray(self):
        return ImgBuffer(path=self._path, img=cv.cvtColor(self.get(), cv.COLOR_RGB2GRAY), domain=self._domain)
    def gray2RGB(self):
        return ImgBuffer(path=self._path, img=np.dstack((self.get(),self.get(),self.get())), domain=self._domain)
        
            

class ImgData():
    def __init__(self, path=None, domain=ImgDomain.Keep):
        self._frames = dict()
        self._domain=domain
        self._min=-1
        self._max=-1
        if path is not None:
            self.load_folder(os.path.abspath(path))

    def load_folder(self, path):
        # Search for frames in folder
        for f in os.listdir(path):
            p = os.path.join(path, f)
            if os.path.isfile(p):
                # Extract frame number, add buffer to dict
                match = re.search("[\.|_](\d+)\.[a-zA-Z]+$", f)
                if match is not None:
                    n = int(match.group(1))
                    self._frames[n] = ImgBuffer(p, domain=self._domain)
                    
                    # Set lowest and highest frame number
                    self._min = n if self._min == -1 else min(self._min, n)
                    self._max = n if self._max == -1 else max(self._max, n)
                else:
                    log.warn("Found file without sequence numbering: {f}")
        
        # Sort it
        self._frames = dict(sorted(self._frames.items()))

        #self._frames = [ImgBuffer(os.path.join(path, f)) for f in os.listdir(path) if os.path.isfile(os.path.join(path, f))]
        log.debug(f"Loaded {len(self._frames)} images from path {path}, bounds ({self._min}, {self._max})")
        
    def get_key_bounds(self):
        return [self._min, self._max]
    
    def get_keys(self):
        return self._frames.keys()

    def get(self, index):
        return list(self._frames.values())[index]
        
    def __getitem__(self, key):
        return self._frames[key]
    
    def __delitem__(self, key):
        del self._frames[key]
    
    def __iter__(self):
        return iter(self._frames.items())

    def __len__(self):
        return len(self._frames)
    
    