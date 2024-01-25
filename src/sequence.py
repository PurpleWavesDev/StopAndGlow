from enum import Enum
import os
import re
import logging as log
from absl import flags

import numpy as np
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
    def __init__(self, path=None, domain=ImgDomain.Keep, video_frame_list=range(0)):
        self._frames = dict()
        self._maskFrame = None
        self._domain=domain
        self._min=-1
        self._max=-1
        if path is not None:
            self.load(os.path.abspath(path), video_frame_list)

    def load(self, path, video_frame_list=range(0)):
        # TODO
        match (os.path.splitext(path)[1]).lower():
            case '':
                # Path, load folder
                self.loadFolder(path)
            case '.mov' | '.mp4':
                # Video
                self.loadVideo(path, video_frame_list)
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
                    id = int(match.group(1))
                    self.append(ImgBuffer(p, domain=self._domain), id)
                else:
                    log.warn("Found file without sequence numbering: {f}")
        
        # Sort it
        self._frames = dict(sorted(self._frames.items()))

        #self._frames = [ImgBuffer(os.path.join(path, f)) for f in os.listdir(path) if os.path.isfile(os.path.join(path, f))]
        log.debug(f"Loaded {len(self._frames)} images from path {path}, bounds ({self._min}, {self._max})")
        
    def loadVideo(self, path, frame_list, video_frames_skip=1):
        # Define paths and sequence names
        # TODO: shuffle mask frame after black frame
        base_dir = os.path.dirname(path)
        seq_name = os.path.splitext(os.path.basename(path))[0]
                    
        img_name_base = os.path.join(base_dir, seq_name, seq_name)
        mask_name_base = os.path.join(base_dir, seq_name+'_mask', seq_name+'_mask')
            
        # Load video & iterate through frames
        vidcap = cv.VideoCapture(path)
        if vidcap is None:
            log.error("Could not load video file '{}'")
            return False
        
        state = VidParseState.PreBlack
        success, frame = vidcap.read()
        frame_number = -1
        frame_count = skip_count = 0
        #black_val = None
        
        while success:
            match state:
                case VidParseState.PreBlack:
                    # Wait for black frame
                    if ImgOp.blackframe(frame):
                        log.debug(f"Found blackframe at frame {frame_count}")
                        state = VidParseState.Black

                        # Save max value of blackframe
                        black_val = np.max(frame)

                case VidParseState.Black:
                    # TODO: Skip first black frame if second one is also black

                    skip_count = (skip_count+1) % video_frames_skip
                    if skip_count == 0:
                        state = VidParseState.Valid
                                        
                case VidParseState.Skip:
                    skip_count = (skip_count+1) % video_frames_skip
                    if skip_count == 0:
                        state = VidParseState.Valid

                case VidParseState.Valid:
                    if frame_number == -1:
                        # Sillhouette frame
                        self._maskFrame = ImgBuffer(path=mask_name_base+f"_{0:03d}.png", img=frame, domain=ImgDomain.sRGB)
                    else:
                        # Abort condition
                        if frame_number >= len(frame_list):
                            #log.debug(f"No new frame at frame {frame_count} with {frame_number} valid frames")
                            break
                        if not ImgOp.blackframe(frame):
                            # Use this frame#
                            id = frame_list[frame_number]
                            log.debug(f"Valid sequence frame {frame_number:3d}, id {id:3d}, found at frame {frame_count} in video")
                            # Append
                            self.append(ImgBuffer(path=img_name_base+f"_{id:03d}.png", img=frame, domain=ImgDomain.sRGB), id)
                        else:
                            log.debug(f"Blackframe at frame {frame_number} / {frame_count}")   
                    # Skip every other frame
                    state = VidParseState.Skip
                    frame_number += 1
                    
            # Next iteration
            success, frame = vidcap.read()
            frame_count +=1
            
    def append(self, img: ImgBuffer, id):
        self._frames[id] = img
        # Set min & max values
        self._min = id if self._min == -1 else min(self._min, id)
        self._max = id if self._max == -1 else max(self._max, id)
            
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
        return iter(self._frames.values())

    def __len__(self):
        return len(self._frames)
    
    