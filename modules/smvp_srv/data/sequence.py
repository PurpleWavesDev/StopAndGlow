from enum import Enum
import os
import re
from pathlib import Path
import logging as log
from absl import flags
import json

import numpy as np
from numpy.typing import ArrayLike
import cv2 as cv

from .imgbuffer import *
from .config import *
from ..utils import imgutils
from ..utils.utils import logging_disabled

class VidParseState(Enum):
    PreBlack = 0,
    Black = 1,
    Skip = 2,
    Valid = 3


class Sequence():
    def __init__(self):
        # Frame list, additional frames and sequences
        self._frames = dict()
        self._preview = ImgBuffer()
        self._data = {}
        
        # Metadata
        self._meta = dict()
        self._meta_changed = False
        self._metafile_name = None
        self._seq_name = ""
        self._base_dir = ""
        
        # Properties
        self._min=-1
        self._max=-1
        self._is_video = False
    
    def __del__(self):
        if self._meta and self._meta_changed:
            # Save metadata
            self.writeMeta()

    def load(self, path, defaults={}, overrides={}):
        if os.path.isdir(path):
            # Apply defaults
            self.setMeta('domain', GetSetting(defaults, 'domain', ImgDomain.Keep.name))

            # Load metadata
            self._metafile_name = os.path.join(path, 'meta.json')
            self.loadMeta()
            
            # Apply overrides
            self.setMeta('domain', GetSetting(overrides, 'domain', self.getMeta('domain')))

            # Load folder
            self.loadFolder(path)
        
        elif os.path.isfile(path) and os.path.splitext(path)[1].lower() in ['.mov', '.mp4']:
            # Apply defaults
            self.setMeta('video_frame_list', GetSetting(defaults, 'video_frame_list', []))
            self.setMeta('video_frames_skip', GetSetting(defaults, 'video_frames_skip', 1))
            self.setMeta('video_frames_offset', GetSetting(defaults, 'video_frames_offset', 0))
        
            # Load metadata
            self._metafile_name = os.path.join(os.path.dirname(path), f'{os.path.splitext(os.path.basename(path))[0]}.json')
            self.loadMeta()
            
            # Apply overrides
            self.setMeta('video_frame_list', GetSetting(overrides, 'video_frame_list', self.getMeta('video_frame_list')))
            self.setMeta('video_frames_skip', GetSetting(overrides, 'video_frames_skip', self.getMeta('video_frames_skip')))
            self.setMeta('video_frames_offset', GetSetting(overrides, 'video_frames_offset', self.getMeta('video_frames_offset')))
            
            # Load Video
            self.loadVideo(path)
            
        else:
            log.error(f"Can't load sequence '{path}'")

                
    def loadFolder(self, path):
        self._base_dir = path
        self._seq_name = os.path.basename(os.path.normpath(path))
        domain = ImgDomain[self.getMeta('domain', ImgDomain.Keep.name)]
        
        # Search for frames in folder
        for f in os.listdir(path):
            p = os.path.join(path, f)
            if os.path.isfile(p):
                # Extract frame number, add buffer to dict
                match = re.search("[\.|_](\d+)\.[a-zA-Z]+$", f)
                preview_match = re.search("[\.|_]preview\.[a-zA-Z]+$", f)
                if match is not None:
                    id = int(match.group(1))
                    self.append(ImgBuffer(p, domain=domain), id)
                elif preview_match is not None:
                    self.setPreview(ImgBuffer(p, domain=domain))
                elif 'meta.json' in f:
                    # Already taken care off
                    pass
                else:
                    log.warn(f"Found file without sequence numbering: {f}")
            else:
                # Load folder as data sequence
                data_seq = Sequence()
                data_seq.loadFolder(p)
                self.setDataSequence(f, data_seq)
        
        # Sort it
        self._frames = dict(sorted(self._frames.items()))

        #self._frames = [ImgBuffer(os.path.join(path, f)) for f in os.listdir(path) if os.path.isfile(os.path.join(path, f))]
        log.debug(f"Loaded {len(self._frames)} images from path {path}, bounds ({self._min}, {self._max})")
        
    def loadVideo(self, path, frame_list, frames_skip, frames_offset, lazy=True):
        # Setup variables
        self._is_video = True
        self._frames_skip = self.getMeta('video_frames_skip', self._frames_skip)
        self._frames_offset = self.getMeta('video_frames_offset', self._frames_offset)
        frame_list = self.getMeta('video_frame_list')
        
        # Define paths and sequence names
        self._seq_name = os.path.splitext(os.path.basename(path))[0]                    
        self._base_dir = os.path.join(os.path.dirname(path), self._seq_name)
        self._img_name_base = os.path.join(self._base_dir, self._seq_name)
            
        # Load video
        self._vidcap = cv.VideoCapture(path)
        self._vid_frame = self._readVideoFrame()
        if self._vid_frame is None:
            log.error(f"Could not load video file '{path}'")
            return False
            
        self._frames = {key: ImgBuffer() for key in frame_list}
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
        while self._vid_frame is not None and (until_frame == -1 or self._vid_frame_number <= until_frame) and self._vid_frame_number < len(self._frames):
            match self._vid_state:
                case VidParseState.PreBlack:
                    # Wait for black frame
                    if imgutils.blackframe(self._vid_frame):
                        log.debug(f"Found blackframe at frame {self._vid_frame_count}")
                        if self._frames_offset > 0:
                            self._vid_state = VidParseState.Black
                        else:
                            self._vid_state = VidParseState.Skip
                        self._skip_count = 0

                        # Save max value of blackframe
                        black_val = np.max(self._vid_frame)

                case VidParseState.Black:
                    # Wait for capture offset
                    self._skip_count = (self._skip_count+1) % self._frames_offset
                    if self._skip_count == 0:
                        self._vid_state = VidParseState.Skip
                                        
                case VidParseState.Skip:
                    # Wait for skip frames
                    self._skip_count = (self._skip_count+1) % (self._frames_skip)
                    if self._skip_count == 0:
                        self._vid_state = VidParseState.Valid

                case VidParseState.Valid:
                    if self._vid_frame_number == -1:
                        # Preview frame
                        self._preview = ImgBuffer(path=self._img_name_base+"_preview", img=self._vid_frame, domain=ImgDomain.sRGB)
                    else:
                        # Abort condition
                        if self._vid_frame_number >= len(self._frames):
                            #log.debug(f"No new frame at frame {self._vid_frame_count} with {self._vid_frame_number} valid frames")
                            break
                        # Append
                        id = self.getKeys()[self._vid_frame_number]
                        self._frames[id] = ImgBuffer(path=self._img_name_base+f"_{id:03d}", img=self._vid_frame, domain=ImgDomain.sRGB)
                        if imgutils.blackframe(self._vid_frame):
                            log.warning(f"Black frame {self._vid_frame_number:3d}, id {id:3d}, found at frame {self._vid_frame_count} in video")
                        elif self._vid_frame_number == len(self._frames)-1:
                            log.debug(f"Last sequence frame {self._vid_frame_number:3d}, id {id:3d}, found at frame {self._vid_frame_count} in video")
                            #pass
                    # Skip every other frame
                    self._vid_state = VidParseState.Skip
                    self._vid_frame_number += 1
                    
            # Next iteration
            self._vid_frame = self._readVideoFrame()
            self._vid_frame_count +=1

        if self._vid_frame is None:
            log.error("Not enough frames in video or sync blackframe hasn't been registered correctly")
            
    def append(self, img: ImgBuffer, id):
        self._frames[id] = img
        # Set min & max values
        self._min = id if self._min == -1 else min(self._min, id)
        self._max = id if self._max == -1 else max(self._max, id)

    def setPreview(self, img: ImgBuffer):
        self._preview = img

    def getPreview(self) -> ImgBuffer:
        return self._preview
        
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
    
    def name(self):
        return self._seq_name
    
    def directory(self):
        return self._base_dir
    
    def saveSequence(self, name: str, base_path: str, format: ImgFormat = ImgFormat.Keep):
        path = os.path.join(base_path, name, name)
        for id in self.getKeys():
            # Get image to load old path
            self[id].get()
            self[id].setPath(f"{path}_{id:03d}")
            self[id].save(format=format)
        if self._preview.get() is not None:
            self._preview.setPath(f"{path}_preview")
            self._preview.save(format=format)
        
        # Metadata
        self._is_video = False
        self._metafile_name = os.path.join(base_path, name, 'meta.json')
        # Delete video metadata
        if 'video_frames_skip' in self._meta: del self._meta['video_frames_skip']
        if 'video_frames_offset' in self._meta: del self._meta['video_frames_offset']
        if 'video_frame_list' in self._meta: del self._meta['video_frame_list']
        if self._meta:
            self.writeMeta()
    
    def convertSequence(self, settings):
        # Scale
        resolution = None
        crop_scale = 1
        
        size = GetSetting(settings, 'size', None)
        crop = GetSetting(settings, 'crop', True)
        if size == 'hd':
            resolution = (1920, 1080)
        elif size == '4k':
            resolution = (3840, 2160)
        if resolution is not None and crop:
            original = self.get(0).resolution()
            crop_scale = resolution[0] / original[0]
        
        # Format
        new_format = GetSetting(settings, 'format', ImgFormat.Keep)
                
        # Iterate over frames and convert
        for id in self.getKeys():
            if self[id].get() is not None:
                self[id] = self[id].convert(resolution, crop, crop_scale, new_format)
        # Don't forget preview 
        if self._preview.get() is not None:
            self._preview = self._preview.convert(resolution, crop, crop_scale, new_format)
        return self
    
    
    ### Additional sequences and frames ###
    
    def getDataKeys(self):
        return list(self._data.keys())
    
    def getDataSequence(self, key) -> 'Sequence':
        if key in self._data:
            return self._data[key]
        return Sequence()
    
    def setDataSequence(self, key, seq: 'Sequence'):
        self._data[key] = seq
            
    
    ### Metadata ###
    
    def loadMeta(self):
        if os.path.isfile(self._metafile_name):
            with open(self._metafile_name, 'r') as f:
                new_meta = json.load(f)
                self._meta = {**self._meta, **new_meta}
                self._meta_changed = new_meta != self._meta
            
    def writeMeta(self):
        if self._metafile_name is not None:
            Path(os.path.split(self._metafile_name)[0]).mkdir(parents=True, exist_ok=True)
            with open(self._metafile_name, 'w') as f:
                json.dump(self._meta, f, indent=4)
                self._meta_changed = False
            log.debug(f"Saved metadata to {self._metafile_name}")
        
    def getMeta(self, key: str, default=None):
        if not key in self._meta:
            return default
        return self._meta[key]
    
    def setMeta(self, key: str, value):
        if not key in self._meta or self._meta[key] != value:
            self._meta[key] = value
            self._meta_changed = True
    
    ### Factories ###
    def ContinueVideoSequence(sequence, path, frame_list, sequence_index):
        seq = Sequence()

        # Setup variables
        seq._is_video = True
        seq._frames_offset = sequence._frames_offset
        seq._frames_skip = sequence._frames_skip
        seq._vidcap = sequence._vidcap
        seq._frames = {key: ImgBuffer() for key in frame_list}
        
        # Define paths and sequence names
        self._seq_name = os.path.splitext(os.path.basename(path))[0]                    
        self._base_dir = os.path.join(os.path.dirname(path), self._seq_name)
        self._img_name_base = os.path.join(self._base_dir, self._seq_name)
        # Get Metadata from other video sequence
        seq._meta = sequence._meta
        expo_meta = seq.getMeta(f'exposure_{sequence_index}')
        if expo_meta is not None:
            seq.setMeta(f'exposure', expo_meta)
            
        # Check vidcap video
        seq._vid_frame = seq._readVideoFrame()
        if seq._vid_frame is None:
            log.error(f"Could not load video file '{path}'")
        
        # Init video states
        seq._vid_state = VidParseState.PreBlack
        seq._vid_frame_number = -1
        seq._vid_frame_count = seq._skip_count = 0
        
        # No lazy loading
        seq.loadFrames()
        return seq

    
    ### Operators / Attributes ###
        
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
    