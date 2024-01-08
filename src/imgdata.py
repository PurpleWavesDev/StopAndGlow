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
from src.img_op import *


IMAGE_DTYPE_FLOAT='float32'
IMAGE_DTYPE_INT='uint8'
# TODO: Unify, input variable?
DATA_BASE_PATH='../HdM_BA/data/'

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


#class PixBuf:
    #def __init__(self, pix):
    
class ImgBuffer:
    def __init__(self, path=None, img: ArrayLike = None, domain: ImgDomain = ImgDomain.Keep):
        self._img=img
        self._domain=domain
        self._format=ImgFormat.Keep
        self._from_file=False
        self.setPath(path)
        
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
            elif self._format != ImgFormat.Keep:
                self.setFormat(ImgFormat.Keep)
    
    def getFormat(self) -> ImgFormat:
        return _format           
    def setFormat(self, img_format: ImgFormat):
        root, ext = os.path.splitext(self._path)
        if img_format != ImgFormat.Keep:
            self._format=img_format
        if self._format != ImgFormat.Keep:
            match img_format:
                case ImgFormat.PNG:
                    self._path = root+".png"
                case ImgFormat.JPG:
                    self._path = root+".jpg"
                case ImgFormat.EXR:
                    self._path = root+".exr"
        else:
            log.warn("No valid format specified, defaulting to PNG")
            self._path = root+".png"
        
    def get(self) -> ArrayLike:
        # Lazy loading
        if self._img is None:
            self.load()
        return self._img

    def set(self, img: ArrayLike, overwrite_file=False):
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
        
    def unload(self, save=False):
        if save and not self._from_file and self._path is not None:
            self.save()
        self._img=None
        
    def save(self, img_format: ImgDomain = ImgFormat.Keep):
        if self._path is not None and self._img is not None:
            if img_format != ImgFormat.Keep:
                # Update path for different format
                self.setFormat(img_format)
                
            # Create folder
            Path(os.path.split(self._path)[0]).mkdir(parents=True, exist_ok=True)
            self._from_file = True
            
            with logging_disabled():
                match self._format:
                    case ImgFormat.EXR:
                        colour.write_image(self._img, self._path, 'float32', method='Imageio')
                    case _: # PNG and JPG
                        colour.write_image(self._img, self._path, 'uint8', method='Imageio')
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
        
    ### Static functions ###

    def FromPix(values, domain: ImgDomain = ImgDomain.sRGB) -> ImgBuffer:
        return ImgBuffer(img=np.array([[values]]).astype(IMAGE_DTYPE_INT)) # TODO: int/float
    
    def SaveBase(img, name, img_format=ImgFormat.PNG):
        path = os.path.abspath(os.path.join(DATA_BASE_PATH, name))
        buffer = ImgBuffer(img=img, path=path)
        buffer.save(img_format)
        return buffer
    
    def SaveEval(img, name, img_format=ImgFormat.PNG):
        return ImgBuffer.SaveBase(img, os.path.join('eval', name), img_format)
            

class ImgData():
    def __init__(self, path=None, domain=ImgDomain.Keep, video_frames_skip=1):
        self._frames = dict()
        self._maskFrame = None
        self._domain=domain
        self._min=-1
        self._max=-1
        self._video_frames_skip=video_frames_skip
        if path is not None:
            self.load(os.path.abspath(path))

    def load(self, path):
        match (os.path.splitext(path)[1]).lower():
            case '':
                # Path, load folder
                self.loadFolder(path)
            case '.mov' | '.mp4':
                # Video
                self.loadVideo(path)
            case _:
                log.error(f"Can't load file {path}")
                
    def loadFolder(self, path):
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
        
    def loadVideo(self, path, seq_name=None):
        # Define paths and sequence names
        # TODO: Lazy loading, with list of frame numbers, shuffle mask frame after black frame
        base_dir = os.path.dirname(path)
        if seq_name is None:
            seq_name = os.path.splitext(os.path.basename(path))[0]
                    
        img_name_base = os.path.join(base_dir, seq_name, seq_name)
        mask_name_base = os.path.join(base_dir, seq_name+'_mask', seq_name+'_mask')
            
        # Load video & iterate through frames
        vidcap = cv.VideoCapture(path)
        if vidcap is None:
            log.error("Could not load video file '{}'")
            return False
        
        class VidParseState(Enum):
            PreBlack = 0,
            Black = 1,
            Skip = 2,
            Valid = 3
        state = VidParseState.PreBlack
        success, frame = vidcap.read()
        frame_number = frame_count = skip_count = 0
        previous = None
        previous2 = None
        #black_val = None
        max_frames=304 #TODO!
        
        while success:
            match state:
                case VidParseState.PreBlack:
                    # Wait for black frame
                    if ImgOp.blackframe(frame):
                        state = VidParseState.Black
                        # Save max value of blackframe and assign mask frame
                        #black_val = np.max(frame)
                        self._maskFrame = ImgBuffer(path=mask_name_base+f"_{0:03d}.png", img=previous2, domain=ImgDomain.sRGB)
                        previous2 = previous = None # Don't need those anymore
                        log.debug(f"Found blackframe at frame {frame_count}")
                    else:
                        # Shuffle frames
                        previous2 = previous
                        previous = frame
                        
                case VidParseState.Black:
                    # Wait for first non-black frame
                    #max_val = np.max(frame)
                    if not ImgOp.blackframe(frame):
                        # Skip this frame, next one is valid
                        # TODO: Possible check max values to find the 'real' blackframe. E.g. if last frame was slightly bright already this one is the valid one!
                        state = VidParseState.Valid
                        log.debug(f"First non-black frame at {frame_count}")
                case VidParseState.Skip:
                    skip_count = (skip_count+1) % self._video_frames_skip
                    if skip_count == 0:
                        state = VidParseState.Valid
                case VidParseState.Valid:
                    # Abort condition
                    #if previous is not None and ImgOp.similar(frame, previous):
                    if frame_number > max_frames:
                        #log.debug(f"No new frame at frame {frame_count} with {frame_number} valid frames")
                        break
                    if not ImgOp.blackframe(frame):
                        # Use this frame
                        self._frames[frame_number] = ImgBuffer(path=img_name_base+f"_{frame_number:03d}.png", img=frame, domain=ImgDomain.sRGB)
                        log.debug(f"Valid sequence frame {frame_number} found at frame {frame_count} in video")
                    else:
                        log.debug(f"Blackframe at frame {frame_number} / {frame_count}")   
                    # Skip every other frame
                    state = VidParseState.Skip
                    frame_number += 1
                    #previous = frame
                    
            # Next iteration
            success, frame = vidcap.read()
            frame_count +=1
            
    def getMaskFrame(self):
        return self._maskFrame
        
    def getKeyBounds(self):
        return [self._min, self._max]
    
    def getKeys(self):
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
    
    