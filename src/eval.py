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
        self.reflection_threshold=230

    # Find center and radius of chromeball
    def find_center(self, imgdata):
        # Locals, use only red channel in frame, as ints
        mask_rgb = imgdata.asInt()
        cb_mask = imgdata.r().asInt().get()
        res_x, res_y = (cb_mask.shape[1],cb_mask.shape[0])
        # Globals; 
        self.cb_center = (0,0)
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
        
        # Masking
        grey = np.full(cb_mask.shape[:2], 0, dtype='uint8')
        alpha = np.zeros(cb_mask.shape[:2], dtype='uint8')
        cv.rectangle(alpha, (0, int(res_y*0.85)), (res_x, res_y), 255, -1)
        alpha = colour.io.convert_bit_depth(cv.GaussianBlur(alpha, (55,55), 200), 'float32')
        beta = (1-alpha)
        # Apply mask
        cb_mask = cv.blendLinear(cb_mask, grey, beta, alpha)
                
        # Binary Filter
        thresh = cv.threshold(cb_mask, 100, 255, cv.THRESH_BINARY + cv.THRESH_OTSU)[1]
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
                Eval.img_save(mask_rgb.get(), 'chromeball_center.png')
        
        
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
                            

    def filter_blackframe(self, imgbuf):
        frame = imgbuf.r().get()
        frame = cv.bitwise_and(frame, frame, mask=self.cb_mask)
        if not np.argmax(frame>self.reflection_threshold):
            # Below threshold 
            return True
        return False


    def find_reflection(self, imgdata, id, debug_img=None):
        # Find reflections in each image
        # Locals
        frame = imgdata.r().asInt().get()
        # Binary filter and mask
        frame = cv.bitwise_and(frame, frame, mask=self.cb_mask)
        frame = cv.threshold(frame, self.reflection_threshold, 255, cv.THRESH_BINARY + cv.THRESH_OTSU)[1]
    
        # Find circle contours
        cnts = cv.findContours(frame, cv.RETR_LIST, cv.CHAIN_APPROX_SIMPLE)
        cnts = cnts[0] if len(cnts) == 2 else cnts[1]
        if len(cnts) == 1:
            # Found reflection
            ((x, y), r) = cv.minEnclosingCircle(cnts[0])
            center = np.array([x, y])
                
            if debug_img is not None:
                cv.circle(debug_img, (int(x+0.5),int(y+0.5)), int(r), (0, 0, 255), 2)
                #cv.line(debug_img, (int(x+0.5),int(y+0.5)), self.cb_center, (0,255,0))
                    
            # Calculate spherical coordinates (O = cb_center, I = center reflection)
            OI = (center - self.cb_center) / self.cb_radius
            OI[1] *= -1
            log.debug(f"Found reflection for frame {id}: {center} x {r}; UV {OI}")
            #length = np.linalg.norm(OI) / cb_radius
            #phi = np.angle(-OI[1]+OI[0]*1j, deg=True)
            #log.info(f"{i}: {phi} - {length}")
            ## Calculate angles relative to z axis
            #z = math.sin(length*math.pi/2)
            #log.info(f">: {z} - {length}")
                
            return OI
                    
        elif len(cnts) >1:
            log.error(f"Frame {id} has {len(cnts)} detected lights, fix threshold / mask.")
            if debug_img is not None:
                for cnt in cnts:
                    ((x, y), r) = cv.minEnclosingCircle(cnt)
                    cv.circle(debug_img, (int(x+0.5),int(y+0.5)), int(r), (255, 0, 0), 2)
        else:
            log.warning(f"Warning: Frame {id} has no detected lights.")
            
        return None


    def img_save(img, name):
        if img.dtype != 'uint8':
            log.debug("Converting image to uint8")
            img = Eval.img_float2byte(img)
            
        file = os.path.join('../HdM_BA/data/eval', name)
        with logging_disabled():
            colour.write_image(img, file, 'uint8', method='Imageio')
        
    def img_float2byte(img):
        return (np.clip(img, 0, 1) * 255).astype('uint8')

