import logging as log
import numpy as np
import math

import cv2 as cv

from src.imgdata import *
from src.config import Config
from src.utils import logging_disabled


class Eval:
    def __init__(self):
        # Settings
        self.reflection_threshold=245
        #self.reflection_min_size=20
        self.reflection_min_ratio=0.013

    # Find center and radius of chromeball
    def findCenter(self, imgdata):
        # Locals, use only red channel in frame, as ints
        mask_rgb = imgdata.asInt()
        cb_mask = imgdata.r().asInt().get()
        res_x, res_y = (cb_mask.shape[1],cb_mask.shape[0])
        # Globals; 
        self.cb_center = np.array([0,0])
        self.cb_radius = 0
        self.cb_mask = np.zeros(cb_mask.shape[:2], dtype="uint8")
        
        # Reduce noise and blend features
        cb_mask = cv.medianBlur(cb_mask, 5)
        #cb_mask = np.clip(cb_mask, 0, 200)
        
        # Canny Edge detect
        cb_mask = cv.Canny(image=cb_mask,
                 threshold1=10.0, # Lower threshold
                 threshold2=100.0, # Upper threshold
                 apertureSize=3,
                 L2gradient=False)
        
        # Dilate and smooth edge
        erosion_size = 1
        blur_size = 1
        kernel = cv.getStructuringElement(cv.MORPH_ELLIPSE, (2 * erosion_size + 1, 2 * erosion_size + 1), (erosion_size, erosion_size))
        cb_mask = cv.dilate(cb_mask, kernel)
        cb_mask = cv.GaussianBlur(cb_mask, (blur_size*2+1,blur_size*2+1), blur_size)
        cb_mask = cv.erode(cb_mask, kernel)
        
        # Masking
        grey = np.full(cb_mask.shape[:2], 0, dtype='uint8')
        alpha = np.zeros(cb_mask.shape[:2], dtype='uint8')
        cv.rectangle(alpha, (0, int(res_y*0.85)), (res_x, res_y), 255, -1)
        alpha = colour.io.convert_bit_depth(cv.GaussianBlur(alpha, (55,55), 200), 'float32')
        beta = (1-alpha)
        # Apply mask
        cb_mask = cv.blendLinear(cb_mask, grey, beta, alpha)
        # Binary Filter
        thresh = cv.threshold(cb_mask, 100, 255, cv.THRESH_BINARY)[1] # + cv.THRESH_OTSU
        
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
            if True:
                cv.circle(mask_rgb.get(), (int(x+0.5),int(y+0.5)), int(r), (0, 0, 255), 2)                    
                Eval.imgSave(mask_rgb.get(), 'chromeball_center')
                
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
                            

    def filterBlackframe(self, imgbuf):
        frame = imgbuf.r().get()
        return ImgOp.blackframe(frame, threshold=self.reflection_threshold, mask=self.cb_mask)

    def findReflection(self, imgdata, id, debug_img=None):
        # Find reflections in each image
        # Locals
        frame = imgdata.r().asInt().get()
        reflection_min_size = self.reflection_min_ratio*self.cb_radius
        # Binary filter and mask
        frame = cv.bitwise_and(frame, frame, mask=self.cb_mask)
        frame = cv.threshold(frame, self.reflection_threshold, 255, cv.THRESH_BINARY)[1]
    
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
            
            # Debug draw discarted circles
            if debug_img is not None:
                for i, cnt in enumerate(cnts):
                    if i != refl_id:
                        ((x, y), r) = cv.minEnclosingCircle(cnt)
                        cv.circle(debug_img, (int(x+0.5),int(y+0.5)), int(r), (0, 0, 255), 2)
            
            if refl_r > reflection_min_size:
                # Calculate spherical coordinates (O = cb_center, I = center reflection)
                OI = (np.asarray(refl_center) - self.cb_center) / self.cb_radius
                OI[1] *= -1
                log.debug(f"Found reflection for frame {id:3d}: ({OI[0]:5.2f}, {OI[1]:5.2f}), radius {refl_r:5.2f}")
                # Debug draw
                if debug_img is not None:
                    cv.circle(debug_img, (int(refl_center[0]+0.5),int(refl_center[1]+0.5)), int(refl_r), (0, 255, 0), 3)
                # Return calculated UV values
                return tuple(OI)
            
            else:
                # Debug draw
                if debug_img is not None:
                    cv.circle(debug_img, (int(refl_center[0]+0.5),int(refl_center[1]+0.5)), int(refl_r), (255, 0, 0), 3)
                log.warning(f"Radius of found reflection too small ({refl_r:.2f}<{reflection_min_size:.2f}), ignoring.")
        else:
            log.warning(f"Frame {id} has no detected reflection.")
        
        return None
    

    ### Static functions ###
    
    def sphericalToLatlong(uv, perspective_distortion=1):
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
        longitude = math.degrees(math.acos(vec[0]/math.cos(latitude)))
        latitude = math.degrees(latitude)
        # Offsets for longitude
        if vec[2] < 0: # Back face
            longitude = (450-longitude)%360
            #print(f"back: {latitude}, {longitude}\n")
        else: # Front face
            longitude = 90+longitude
            #print(f"front: {latitude}, {longitude}\n")
        return (latitude, longitude)


    def imgSave(img, name, img_format=ImgFormat.PNG):
        BASE_PATH_EVAL='../HdM_BA/data/eval'
        img = ImgBuffer(img=img, path=os.path.join(BASE_PATH_EVAL, name))
        img.save(img_format)


class ImgOp:
    def similar(img1, img2, threshold=0.1, mask=None) -> bool:
        if mask is not None:
            img = cv.bitwise_and(img, img, mask=mask)
        return not np.argmax((img1-img2)>=threshold)
    
    def blackframe(img, threshold=0.2, mask=None) -> bool:
        if mask is not None:
            img = cv.bitwise_and(img, img, mask=mask)
        return not np.argmax(img>=threshold)

def rotationMatrix(axis, theta):
    """
    Return the rotation matrix associated with counterclockwise rotation about
    the given axis by theta radians.
    """
    axis = np.asarray(axis)
    axis = axis / math.sqrt(np.dot(axis, axis))
    a = math.cos(theta / 2.0)
    b, c, d = -axis * math.sin(theta / 2.0)
    aa, bb, cc, dd = a * a, b * b, c * c, d * d
    bc, ad, ac, ab, bd, cd = b * c, a * d, a * c, a * b, b * d, c * d
    return np.array([[aa + bb - cc - dd, 2 * (bc + ad), 2 * (bd - ac)],
                     [2 * (bc - ad), aa + cc - bb - dd, 2 * (cd + ab)],
                     [2 * (bd + ac), 2 * (cd - ab), aa + dd - bb - cc]])
