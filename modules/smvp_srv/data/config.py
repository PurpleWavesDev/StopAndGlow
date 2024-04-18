import os
import json 
import math
from pathlib import Path

class Config:
    def GetDefaults():
        return {
            # General
            'loglevel': 'debug',
            'resolution': [1920, 1080],
            # Folders and default files
            'seq_folder': '../HdM_BA/data/capture',
            'cal_folder': '../HdM_BA/data/calibration',
            'cal_name': 'lightdome.json',
            'hdri_folder': '../HdM_BA/data/hdri',
            'hdri_name': 'hdri.exr',
            # Config TODO: self-referencing? should replace path variable or only be available there
            'config_folder': '../HdM_BA/data/config',
            'config_name': 'config.json',
            # Capture settings
            'hdr_capture': True,
            'hdr_bracket_num': 2,
            'hdr_bracket_stops': 2,
            'capture_exposure': "1/200",
            'capture_fps': 25,
            'capture_frames_skip': 3,
            'capture_dmx_repeat': 0,
            'capture_max_addr': 310,
            # Processing settings
            'hdri_rotation': 0.0,
        }

    def __init__(self, path=None):
        # Assign defaults
        self._config = Config.GetDefaults()
        self._changed = False
        self._path = path
        
        if self._path is not None:
            if os.path.exists(self._path):
                self.load(self._path)
            else:
                self.save(self._path)
    
    def load(self, path=None):
        if path is not None:
            self._path = path
        
        if self._path is not None:
            with open(self._path, "r") as file:
                data = json.load(file)
                self._config = {**self._config, **data}

    def save(self, path=None):
        if path is not None:
            self._path = path
            
        if self._path is not None:
            Path(os.path.dirname(self._path)).mkdir(parents=True, exist_ok=True)
            with open(self._path, "w") as file:
                json.dump(self._config, file, indent=4)
            self._changed = False
    
    def get(self) -> dict:
        return dict(self._config)
    
    def __getitem__(self, key):
        return self._config[key]

    def __len__(self):
        return len(self._config)
        
    def __delitem__(self, key):
        del self._config[key]
    
    def __iter__(self):
        return iter(self._config)

### General dict helpers ###
def GetSetting(settings, key, default=None, default_for_empty=False, dtype=None):
    if key in settings:
        if not default_for_empty or settings[key] != '':
            if dtype != None:
                if dtype == bool:
                    return settings[key].lower() in ['true', '1', 't', 'y', 'yes']
                return dtype(settings[key])
            return settings[key]
    return default

def SetDefault(settings, key, val):
    if not key in settings: settings[key] = val
