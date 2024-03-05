import logging as log
import numpy as np
import math

import cv2 as cv
import taichi as ti

from src.imgdata import *
from src.sequence import Sequence
from src.img_op import *
from src.config import Config
from src.utils import logging_disabled
from src.mathutils import *
from src.renderer.renderer import *


class Calibrate(Renderer):
    def __init__(self):
        pass
        
    def load(self, img_seq: Sequence):
        pass
    
    def get(self) -> Sequence:
        return Sequence()
    def getCalibration(self) -> Config:
        return self._config
    
    def process(self, img_seq: Sequence, config: Config, settings={'threshold': 245, 'min_size_ratio': 0.011, 'interactive': False}):
        self._view_idx = 0
        # Settings
        self._threshold = settings['threshold'] if 'threshold' in settings else 245
        self._min_size_ratio = settings['min_size_ratio'] if 'min_size_ratio' in settings else 0.011
        self._interactive = settings['interactive'] if 'interactive' in settings else False
        
        # Save members
        self._sequence = img_seq
        self._config = Config()
        
        log.info(f"Processing calibration sequencee with {len(img_seq)} frames")

        # Find center of chrome ball
        self.findCenter()
        # Find reflections
        self.findReflections()
                
    def setSequence(self, img_seq: Sequence):
        pass

    # Render settings
    def getRenderModes(self) -> list:
        return ["Sequence", "Chromeball", "Threshold", "Result"]
    def getRenderSettings(self, render_mode) -> RenderSettings:
        return RenderSettings(req_keypress_events=True)
    def keypressEvent(self, event_key):
        if event_key in ['a']: # Left
            self._view_idx = (len(self._sequence)+self._view_idx-1) % len(self._sequence)
        elif event_key in ['d']: # Right
            self._view_idx = (self._view_idx+1) % len(self._sequence)
        elif event_key in ['w']:
            pass
        elif event_key in ['s']:
            pass

    # Rendering
    def render(self, render_mode, buffer, hdri=None):
        match render_mode:
            case 0: # Sequence
                #buffer.from_numpy(self._sequence.getMaskFrame().get())
                buffer.from_numpy(self._sequence.get(self._view_idx).get())
            case 1: # Chromeball
                buffer.from_numpy(self._mask_rgb.get())
            case 2: # Threshold
                buffer.from_numpy(np.dstack([self.cb_mask, self.cb_mask, self.cb_mask]))
            case 3: # Result
                buffer.from_numpy(self._reflections)


    # Find center and radius of chromeball
    # TODO: cv.bilateralFilter respects edges, could be used here
    def findCenter(self):
        # Frames
        self._mask_rgb = self._sequence.getMaskFrame().asInt()
        cb_filtered = self._mask_rgb.r().get()
        res_x, res_y = self._mask_rgb.resolution()
        
        # Calibration values and fields
        self.cb_mask = np.zeros(cb_filtered.shape[:2], dtype="uint8")
        self.cb_center = np.array([0,0])
        self.cb_radius = 0
        
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
        blur_size = 1
        kernel = cv.getStructuringElement(cv.MORPH_ELLIPSE, (2 * erosion_size + 1, 2 * erosion_size + 1), (erosion_size, erosion_size))
        cb_filtered = cv.dilate(cb_filtered, kernel)
        cb_filtered = cv.GaussianBlur(cb_filtered, (blur_size*2+1,blur_size*2+1), blur_size)
        cb_filtered = cv.erode(cb_filtered, kernel)
        
        # Masking
        grey = np.full(cb_filtered.shape[:2], 0, dtype='uint8')
        alpha = np.zeros(cb_filtered.shape[:2], dtype='uint8')
        cv.rectangle(alpha, (0, int(res_y*0.85)), (res_x, res_y), 255, -1)
        alpha = colour.io.convert_bit_depth(cv.GaussianBlur(alpha, (55,55), 200), 'float32')
        beta = (1-alpha)
        # Apply mask
        cb_filtered = cv.blendLinear(cb_filtered, grey, beta, alpha)
        # Binary Filter
        thresh = cv.threshold(cb_filtered, 100, 255, cv.THRESH_BINARY)[1] # + cv.THRESH_OTSU
        
        # Save image if not in interactive mode
        if not self._interactive:
            ImgOp.SaveEval(thresh, 'chromeball_filtered')
        
        # Find circle contours
        cnts = cv.findContours(thresh, cv.RETR_EXTERNAL, cv.CHAIN_APPROX_SIMPLE)
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
            
            # Draw circle in RGB image
            cv.circle(self._mask_rgb.get(), (int(x+0.5),int(y+0.5)), int(r), (0, 0, 255), 2)                    
            # Save image if not in interactive mode
            if not self._interactive:
                ImgOp.SaveEval(self._mask_rgb.get(), 'chromeball_center')
                
            log.info(f"Found chrome ball at ({self.cb_center[0]:5.2f}, {self.cb_center[1]:5.2f}), radius {self.cb_radius:5.2f}")
        else:
            log.error("Did not find chrome ball")
        
        
        # Don't need full resolution
        #scale=0.5
        #cb_mask = cv.resize(cb_mask, None, fx=scale, fy=scale)# (int(cb_mask.shape[1]/scale_div), int(cb_mask.shape[0]/scale_div)), interpolation=cv.INTER_NEAREST)

        # High pass
        #intensity=15
        #cb_mask = np.abs(cb_mask - cv.GaussianBlur(cb_mask, (intensity*2+1,intensity*2+1), 50).astype('int16')).astype('uint8')
        #cb_mask = cb_mask - cv.GaussianBlur(cb_mask, (intensity*2+1,intensity*2+1), intensity) + 127
        
        
        
        
        # Detect circles
        #circles = cv.HoughCircles(cb_mask, cv.HOUGH_GRADIENT,
        #                            dp=1, # Resolution
        #                            minDist=1,
        #                            param1=50, # Higher threshold for threshold detection
        #                            param2=110, # Accumulator threshold for centers, Higher=Less circles
        #                            minRadius=int(x/6), maxRadius=int(y/2))
        
        #if circles is not None:
        #    log.debug(f"Found {len(circles[0])} circles!")
        #    circles = np.uint16(np.around(circles))
        #    for i in circles[0, :]:
        #        cb_center = np.array((i[0], i[1]))
        #        cb_radius = i[2]
        #        # Draw circle
        #        cv.circle(mask_rgb,(i[0],i[1]),i[2],(0,255,0),2)
        #        cv.circle(mask_rgb,(i[0],i[1]),2,(0,0,255),3)
                            
    def findReflections(self):
        # Loop through all calibration frames
        self._reflections = self._mask_rgb.get()
        for id, img in self._sequence:
            if not self.filterBlackframe(img):
                # Process frame
                uv = self.findReflection(img, id)
                if uv is not None:
                    self._config.addLight(id, uv, Calibrate.SphericalToLatlong(uv))
                #img.unload()
            else:
                log.debug(f"Found blackframe '{id}'")
                #img.unload()
        
        # Save debug image
        if not self._interactive:
            ImgOp.SaveEval(self._reflections, "reflections")


    ### Helpers ###
    
    def filterBlackframe(self, imgbuf):
        frame = imgbuf.r().get()
        return ImgOp.blackframe(frame, threshold=self._threshold, mask=self.cb_mask)

    def findReflection(self, imgdata, id):
        # Find reflections in each image
        # Locals
        frame = imgdata.r().asInt().get()
        reflection_min_size = self._min_size_ratio*self.cb_radius
        # Binary filter and mask
        frame = cv.bitwise_and(frame, frame, mask=self.cb_mask)
        frame = cv.threshold(frame, self._threshold, 255, cv.THRESH_BINARY)[1]
    
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
                log.debug(f"Found reflection for frame {id:3d}: ({OI[0]:5.2f}, {OI[1]:5.2f}), radius {refl_r:5.2f}")
                # Draw valid reflection
                cv.circle(self._reflections, (int(refl_center[0]+0.5),int(refl_center[1]+0.5)), int(refl_r), (0, 255, 0), 3)
                return tuple(OI) # UV value
            
            else:
                # Draw too-small reflection
                cv.circle(self._reflections, (int(refl_center[0]+0.5),int(refl_center[1]+0.5)), int(refl_r), (255, 0, 0), 3)
                log.warning(f"Radius of found reflection too small ({refl_r:.2f}<{reflection_min_size:.2f}), ignoring.")
        else:
            log.warning(f"Frame {id} has no detected reflection.")
        
        return None
    

    ### Static functions ###
    
    def SphericalToLatlong(uv, perspective_distortion=1):
        uv=np.array(uv)
        # First get the length of the UV coordinates
        length = np.linalg.norm(uv)
        uv_norm = uv/length
        
        # Get direction of light source
        vec = np.array([0,0,1]) # Vector pointing into camera
        axis = np.array([-uv_norm[1],uv_norm[0],0]) # Rotation axis that is the direction of the reflection rotated 90° on Z
        theta = math.asin(length)*2 # Calculate the angle to the reflection which is two times the angle of the normal on the sphere
        vec = np.dot(rotationMatrix(axis, theta), vec) # Rotate vector to light source
        
        # Calculate Latitude and Longitude
        latitude = math.asin(vec[1])
        longitude = 90-math.degrees(math.acos(vec[0]/math.cos(latitude))) # -90 to 90 degree front side
        latitude = math.degrees(latitude)
        # Offsets for longitude
        if vec[2] < 0: # Back side
            longitude = (180-longitude) # 90 to 270 degree, correct value

        return (latitude, (longitude+360) % 360) # make longitude all positive

