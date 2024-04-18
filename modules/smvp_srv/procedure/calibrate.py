import logging as log
import numpy as np
import math
from copy import copy, deepcopy

import cv2 as cv
import taichi as ti

from ..data import *
from ..hw import Calibration
from ..utils import *
from ..viewer.viewer import *

class Calibrate(Viewer):
    def __init__(self):
        self._recalc = False
        self._cal = Calibration()
        self._sequence = Sequence()
    
    ## Viewer functions
    def setResolution(self, resolution):
        self._resolution = resolution
    
    def getModes(self) -> list:
        return ["EdgeFilter", "Chromeball", "Reflections", "Sequence"]
    
    def setMode(self, mode):
        self._mode = mode
        self.findCenter()
        self.findReflections()
        self._recalc = False
        
    def getRenderSettings(self, mode) -> RenderSettings:
        return RenderSettings(as_int=True, req_keypress_events=True, req_inputs=True)

    def keypressEvent(self, event_key):
        if self._mode <=1:
            if event_key in ['a']: # Left
                self._mask_blur_size = max(0, self._mask_blur_size-1)
                self._recalc = True
            elif event_key in ['d']: # Right
                self._mask_blur_size += 1
                self._recalc = True
        elif self._mode == 2:
            # Inputs for reflections
            if event_key in [ti.ui.UP]:
                self._refl_threshold += 1
                self._recalc = True
            elif event_key in [ti.ui.DOWN]:
                self._refl_threshold = max(0, self._refl_threshold-1)
                self._recalc = True
            if event_key in ['w']:
                self._min_size_ratio *= 1.1
                self._recalc = True
            elif event_key in ['s']:
                self._min_size_ratio /= 1.1
                self._recalc = True

        else:
            if event_key in ['a']: # Left
                self._view_idx = (len(self._sequence)+self._view_idx-1) % len(self._sequence)
            elif event_key in ['d']: # Right
                self._view_idx = (self._view_idx+1) % len(self._sequence)
            elif event_key in ['w']:
                pass
            elif event_key in ['s']:
                pass
    
    def inputs(self, window, time_frame):
        if self._mode <=1:
        # Inputs for EdgeFilter
            if window.is_pressed(ti.ui.UP):
                self._mask_threshold += int(20*time_frame)
                self._recalc = True
            if window.is_pressed(ti.ui.DOWN):
                self._mask_threshold -= int(20*time_frame)
                self._recalc = True
            if window.is_pressed('s'):
                self._rect_mask_offset += (0.05 * time_frame)
                self._recalc = True
            if window.is_pressed('w'):
                self._rect_mask_offset -= (0.05 * time_frame)
                self._recalc = True
                
        if self._recalc:
            if self._mode <= 1:
                self.findCenter()
            elif self._mode == 2:
                self.findReflections()
            self._recalc = False
    
    def render(self, buffer, time_frame):
        match self._mode:
            case 0: # EdgeFilter
                buffer.from_numpy(np.dstack([self._cb_edges, self._cb_edges, self._cb_edges]))
            case 1: # Chromeball
                buffer.from_numpy(cv.bitwise_and(self._mask_rgb, self._mask_rgb, mask=self.cb_mask))
            case 2: # Reflections
                buffer.from_numpy(self._reflections)
            case 3: # Sequence
                buffer.from_numpy(self._sequence.get(self._view_idx).get())


    ## Data functions (set sequence & return cal)
    def setSequence(self, img_seq: Sequence):
        self._sequence = img_seq
        self._sequence.convertSequence({'domain': ImgDomain.sRGB, 'as_int': True})
    
    # Data return
    def getCalibration(self) -> Calibration:
        return self._cal
    
    
    ## Processing methodes
    def process(self, settings={'threshold': 245, 'min_size_ratio': 0.011}, interactive=False):
        self._view_idx = 0
        # Settings
        self._rect_mask_offset = 0.85
        self._mask_threshold = 100
        self._mask_blur_size = 1
        if self._sequence.getMeta('focal_length') is None:
            log.warning("Can't do perspective correction without focal_length metadata")
        self._refl_threshold = GetSetting(settings, 'threshold', 245, dtype=int)
        self._min_size_ratio = GetSetting(settings, 'min_size_ratio', 0.011, dtype=float)
        
        self._interactive = interactive
        
        
        log.info(f"Processing calibration sequencee with {len(self._sequence)} frames")
                
        # Find center of chrome ball and all reflections
        self.findCenter()
        self.findReflections()
        self._recalc = False
        

    # Find center and radius of chromeball
    # TODO: cv.bilateralFilter respects edges, could be used here
    def findCenter(self):
        # Copy Frames
        mask_frame = self._sequence.getPreview().asInt()
        self._mask_rgb = np.copy(mask_frame.get())
        cb_filtered = np.copy(mask_frame.r().get())
        res_x, res_y = mask_frame.resolution()
        
        # Calibration values and fields
        self.cb_mask = np.zeros(cb_filtered.shape[:2], dtype="uint8")
        self.cb_center = np.array([0,0])
        self.cb_radius = 0
        self._viewing_angle_by2 = 0
        
        # Reduce noise and blend features
        cb_filtered = cv.medianBlur(cb_filtered, 5)
        #cb_filtered = np.clip(cb_filtered, 0, 200)
        
        # Canny Edge detect
        cb_filtered = cv.Canny(image=cb_filtered,
                 threshold1=10.0, # Lower threshold
                 threshold2=100.0, # Upper threshold
                 apertureSize=3,
                 L2gradient=False)
        
        # Dilate and smooth edge
        erosion_size = 1
        kernel = cv.getStructuringElement(cv.MORPH_ELLIPSE, (2 * erosion_size + 1, 2 * erosion_size + 1), (erosion_size, erosion_size))
        cb_filtered = cv.dilate(cb_filtered, kernel)
        cb_filtered = cv.GaussianBlur(cb_filtered, (self._mask_blur_size*2+1,self._mask_blur_size*2+1), self._mask_blur_size)
        cb_filtered = cv.erode(cb_filtered, kernel)
        
        # Masking bottom part of the image
        grey = np.full(cb_filtered.shape[:2], 0, dtype='uint8')
        alpha = np.zeros(cb_filtered.shape[:2], dtype='uint8')
        cv.rectangle(alpha, (0, int(res_y*self._rect_mask_offset)), (res_x, res_y), 255, -1)
        alpha = colour.io.convert_bit_depth(cv.GaussianBlur(alpha, (55,55), 200), 'float32')
        beta = (1-alpha)
        # Apply mask
        cb_filtered = cv.blendLinear(cb_filtered, grey, beta, alpha)
        # Binary Filter
        self._cb_edges = cv.threshold(cb_filtered, self._mask_threshold, 255, cv.THRESH_BINARY)[1] # + cv.THRESH_OTSU
        
        # Save image if not in interactive mode
        if not self._interactive:
            imgutils.SaveEval(self._cb_edges, 'chromeball_filtered')
        
        # Find circle contours
        cnts = cv.findContours(self._cb_edges, cv.RETR_EXTERNAL, cv.CHAIN_APPROX_SIMPLE)
        cnts = cnts[0] if len(cnts) == 2 else cnts[1]
        all_cnts = None
        for i, cnt in enumerate(cnts):
            if i == 0:
                all_cnts=cnt
            else:
                all_cnts = np.append(all_cnts, cnt, axis=0)

        if all_cnts is not None:
            # Found contour, get circle
            ((x, y), r) = cv.minEnclosingCircle(all_cnts)
            self.cb_center = np.array([x, y])
            self.cb_radius = r
            cv.circle(self.cb_mask, (int(x+0.5),int(y+0.5)), int(r), 255, -1)
            # Add linear mask at bottom
            self.cb_mask = cv.blendLinear(self.cb_mask, grey, beta, alpha)

            # Draw circle in RGB image
            cv.circle(self._mask_rgb, (int(x+0.5),int(y+0.5)), int(r), (0, 0, 255), 2)                    
            # Save image if not in interactive mode
            if not self._interactive:
                imgutils.SaveEval(self._mask_rgb, 'chromeball_center')
                log.info(f"Found chrome ball at ({self.cb_center[0]:5.2f}, {self.cb_center[1]:5.2f}), radius {self.cb_radius:5.2f}")
                
            # Calculate viewing angle
            if self._sequence.getMeta('focal_length', 135) is not None: # TODO: Remove default as soon as metadata works
                sensor = self._sequence.getMeta('sensor_size', (22.0, 15.0)) # APS-C is default, only works without cropping
                f = self._sequence.getMeta('focal_length', 135) # TODO
                size_on_sensor = sensor[0] / (res_x/(self.cb_radius*2))
                self._viewing_angle_by2 = math.atan(size_on_sensor/(2*f))
        else:
            log.error("Did not find chrome ball")

        # High pass
        #intensity=15
        #cb_mask = np.abs(cb_mask - cv.GaussianBlur(cb_mask, (intensity*2+1,intensity*2+1), 50).astype('int16')).astype('uint8')
        #cb_mask = cb_mask - cv.GaussianBlur(cb_mask, (intensity*2+1,intensity*2+1), intensity) + 127
        
                                    
    def findReflections(self):
        # Clear calibration
        self._cal = Calibration()
        # Loop through all calibration frames
        self._reflections = copy(self._mask_rgb)
        for id, img in self._sequence:
            img = np.copy(img.r().asInt().get())
            if not self.filterBlackframe(img):
                # Process frame
                uv = self.findReflection(img, id)
                if uv is not None:
                    self._cal.addLight(id, uv, LightPosition.MirrorballToCoordinates(uv, self._viewing_angle_by2))
            elif not self._interactive:
                log.debug(f"Found blackframe '{id}'")
            if not self._interactive:
                img.unload()
        
        # Save debug image
        if not self._interactive:
            imgutils.SaveEval(self._reflections, "reflections")


    ### Helpers ###
    
    def filterBlackframe(self, frame):
        return imgutils.blackframe(frame, threshold=self._refl_threshold, mask=self.cb_mask)

    def findReflection(self, frame, id):
        # Find reflections in each image
        # Locals
        reflection_min_size = self._min_size_ratio*self.cb_radius
        # Binary filter and mask
        frame = cv.bitwise_and(frame, frame, mask=self.cb_mask)
        frame = cv.threshold(frame, self._refl_threshold, 255, cv.THRESH_BINARY)[1]
    
        # Find circle contours
        cnts = cv.findContours(frame, cv.RETR_LIST, cv.CHAIN_APPROX_SIMPLE)
        cnts = cnts[0] if len(cnts) == 2 else cnts[1]
        if len(cnts) >= 1:
            refl_center = (0,0)
            refl_r = 0
            refl_id = 0
            for i, cnt in enumerate(cnts):
                # Found reflection
                ((x, y), r) = cv.minEnclosingCircle(cnt)
                if r > refl_r:
                    refl_id = i
                    refl_r = r
                    refl_center = (x, y)
            
            # Draw discarted reflections
            for i, cnt in enumerate(cnts):
                if i != refl_id:
                    ((x, y), r) = cv.minEnclosingCircle(cnt)
                    cv.circle(self._reflections, (int(x+0.5),int(y+0.5)), int(r), (0, 0, 255), 2)
            
            if refl_r > reflection_min_size:
                # Calculate spherical coordinates (O = cb_center, I = center reflection)
                OI = (np.asarray(refl_center) - self.cb_center) / self.cb_radius
                OI[1] *= -1
                if not self._interactive:
                    log.debug(f"Found reflection for frame {id:3d}: ({OI[0]:5.2f}, {OI[1]:5.2f}), radius {refl_r:5.2f}")
                # Draw valid reflection
                cv.circle(self._reflections, (int(refl_center[0]+0.5),int(refl_center[1]+0.5)), int(refl_r), (0, 255, 0), 3)
                return tuple(OI) # UV value
            
            else:
                # Draw too-small reflection
                cv.circle(self._reflections, (int(refl_center[0]+0.5),int(refl_center[1]+0.5)), int(refl_r), (255, 0, 0), 3)
                if not self._interactive:
                    log.warning(f"Radius of found reflection too small ({refl_r:.2f}<{reflection_min_size:.2f}), ignoring.")
        elif not self._interactive:
            log.warning(f"Frame {id} has no detected reflection.")
        
        return None
    
