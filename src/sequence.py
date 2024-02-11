from enum import Enum
import os
import re
import logging as log
from absl import flags

import numpy as np
from numpy.typing import ArrayLike
import cv2 as cv

from src.imgdata import *
from src.img_op import *
from src.utils import logging_disabled

class VidParseState(Enum):
    PreBlack = 0,
    Black = 1,
    Skip = 2,
    Valid = 3


class Sequence():
    def __init__(self):
        self._frames = dict()
        self._maskFrame = None
        self._min=-1
        self._max=-1
        self._is_video = False

    def load(self, path, domain=ImgDomain.Keep, video_frame_list=range(0)):
        # TODO
        match (os.path.splitext(path)[1]).lower():
            case '':
                # Path, load folder
                self.loadFolder(path, domain)
            case '.mov' | '.mp4':
                # Video
                self.loadVideo(path, video_frame_list)
            case _:
                log.error(f"Can't load file {path}")
                
    def loadFolder(self, path, domain=ImgDomain.Keep):
        # Search for frames in folder
        for f in os.listdir(path):
            p = os.path.join(path, f)
            if os.path.isfile(p):
                # Extract frame number, add buffer to dict
                match = re.search("[\.|_](\d+)\.[a-zA-Z]+$", f)
                if match is not None:
                    id = int(match.group(1))
                    self.append(ImgBuffer(p, domain=domain), id)
                else:
                    log.warn("Found file without sequence numbering: {f}")
        
        # Sort it
        self._frames = dict(sorted(self._frames.items()))

        #self._frames = [ImgBuffer(os.path.join(path, f)) for f in os.listdir(path) if os.path.isfile(os.path.join(path, f))]
        log.debug(f"Loaded {len(self._frames)} images from path {path}, bounds ({self._min}, {self._max})")
        
    def loadVideo(self, path, frame_list, video_frames_skip=1, lazy=True):
        # Setup variables
        self._is_video = True
        self._vid_frames_skip = video_frames_skip
        
        # Define paths and sequence names
        base_dir = os.path.dirname(path)
        seq_name = os.path.splitext(os.path.basename(path))[0]
                    
        self._img_name_base = os.path.join(base_dir, seq_name, seq_name)
        self._mask_name_base = os.path.join(base_dir, seq_name+'_mask', seq_name+'_mask')
            
        # Load video
        self._vidcap = cv.VideoCapture(path)
        self._vid_frame = self._readVideoFrame()
        if self._vid_frame is None:
            log.error(f"Could not load video file '{path}'")
            return False
            
        self._frames = {key: None for key in frame_list}        
        self._vid_state = VidParseState.PreBlack
        self._vid_frame_number = -1
        self._vid_frame_count = self._skip_count = 0
        
        # Lazy loading
        if not lazy:
            self.loadFrames()
        else:
            self.loadFrames(0)
        return True
        
    def loadFrames(self, until_frame=-1):
        # Iterate through frames until max
        while self._vid_frame is not None and (until_frame == -1 or self._vid_frame_number <= until_frame):
            match self._vid_state:
                case VidParseState.PreBlack:
                    # Wait for black frame
                    if ImgOp.blackframe(self._vid_frame):
                        log.debug(f"Found blackframe at frame {self._vid_frame_count}")
                        self._vid_state = VidParseState.Black

                        # Save max value of blackframe
                        black_val = np.max(self._vid_frame)

                case VidParseState.Black:
                    # TODO: Skip first black frame if second one is also black

                    self._skip_count = (self._skip_count+1) % self._vid_frames_skip
                    if self._skip_count == 0:
                        self._vid_state = VidParseState.Valid
                                        
                case VidParseState.Skip:
                    self._skip_count = (self._skip_count+1) % self._vid_frames_skip
                    if self._skip_count == 0:
                        self._vid_state = VidParseState.Valid

                case VidParseState.Valid:
                    if self._vid_frame_number == -1:
                        # Sillhouette frame
                        self._maskFrame = ImgBuffer(path=self._mask_name_base+f"_{0:03d}.png", img=self._vid_frame, domain=ImgDomain.sRGB)
                    else:
                        # Abort condition
                        if self._vid_frame_number >= len(self._frames):
                            #log.debug(f"No new frame at frame {self._vid_frame_count} with {self._vid_frame_number} valid frames")
                            break
                        if not ImgOp.blackframe(self._vid_frame):
                            # Use this frame#
                            id = self.getKeys()[self._vid_frame_number]
                            log.debug(f"Valid sequence frame {self._vid_frame_number:3d}, id {id:3d}, found at frame {self._vid_frame_count} in video")
                            # Append
                            self._frames[id] = ImgBuffer(path=self._img_name_base+f"_{id:03d}.png", img=self._vid_frame, domain=ImgDomain.sRGB)
                        else:
                            log.debug(f"Blackframe at frame {self._vid_frame_number} / {self._vid_frame_count}")   
                    # Skip every other frame
                    self._vid_state = VidParseState.Skip
                    self._vid_frame_number += 1
                    
            # Next iteration
            self._vid_frame = self._readVideoFrame()
            self._vid_frame_count +=1
            
    def append(self, img: ImgBuffer, id):
        self._frames[id] = img
        # Set min & max values
        self._min = id if self._min == -1 else min(self._min, id)
        self._max = id if self._max == -1 else max(self._max, id)
            
    def getMaskFrame(self) -> ImgBuffer:
        return self._maskFrame
        
    def getKeyBounds(self):
        return [self._min, self._max]
    
    def getKeys(self):
        return list(self._frames.keys())

    def get(self, index) -> ImgBuffer:
        if self._is_video:
            self.loadFrames(index)
        return list(self._frames.values())[index]
    
    def set(self, index, img: ImgBuffer):
        # TODO: Gets overwritten when using a video that is not loaded yet
        self[self.getKeys()[index]] = img
        
    def __getitem__(self, key):
        if self._is_video:
            self.loadFrames(self.getKeys().index(key))
        return self._frames[key]
    
    def __setitem__(self, key, item):
        # TODO: Gets overwritten when using a video that is not loaded yet
        self._frames[key] = item
    
    def __delitem__(self, key):
        del self._frames[key]
    
    def __iter__(self):
        # TODO: Lazy loading not working with __iter__
        if self._is_video:
            self.loadFrames(-1)
        return iter(self._frames.items())

    def __len__(self):
        return len(self._frames)
    
    
    def _readVideoFrame(self) -> ArrayLike:
        if self._vidcap is None:
            return None
        
        suc, frame = self._vidcap.read()
        if not suc:
            return None
        
        return cv.cvtColor(frame, cv.COLOR_BGR2RGB)
    