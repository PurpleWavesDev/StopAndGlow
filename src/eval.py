import logging as log
import numpy as np
import math

import cv2 as cv
#from PIL import Image
import imutils

from src.imgdata import *
from src.config import Config

class Eval:
    def __init__(self):
        # Settings
        self.thresh_min=100
        self.thresh_max=255

    # Find center and radius of chromeball
    def find_center(self, imgdata):
        # use red channel only, as ints
        cb_mask = imgdata.g().asInt().get()
        cb_center = (0,0)
        cb_radius = 0

        # Reduce noise
        cb_mask = cv.medianBlur(cb_mask, 15)
        # High pass
        intensity=25
        cb_mask = cb_mask - cv.GaussianBlur(cb_mask, (intensity*2+1,intensity*2+1), 50) + 127
        
        #cv.smooth(cb_mask, cb_mask, cv.CV_GAUSSIAN, 5, 5)
        #cv.erode(cb_mask, cb_mask, None, 10)
        #cv.dilate(cb_mask, cb_mask, None, 10)
        #cv.canny(cb_mask, cb_mask, 5, 70, 3)
        #cv.smooth(cb_mask, cb_mask, cv.CV_GAUSSIAN, 15, 15)
        
        # TODO: Resize and HoughCircles functions just block, wtf 
        #cb_mask = Image.resize((6960/5,3904/5))
        #cb_mask = imutils.resize(cb_mask, width=6960/5)
        #cb_mask = cv.resize(cb_mask,(6960/10,3904/10),interpolation=cv.INTER_NEAREST)
        cb_mask = cb_mask[::4, ::4]
        

        x,y = (cb_mask.shape[1],cb_mask.shape[0])
        circles = cv.HoughCircles(cb_mask, cv.HOUGH_GRADIENT_ALT, 20, minDist=10,
                                    param1=10, # Edge detect filter
                                    param2=50, # Threshold for detections
                                    minRadius=x/3, maxRadius=y)
                
        if circles is not None:
            lg.debug(f"Found {len(circles)} circles!")
            circles = np.uint16(np.around(circles))
            for i in circles[0, :]:
                cb_center = np.array((i[0], i[1]))
                cb_radius = i[2]
                    
        Eval.img_save(np.dstack((cb_mask, cb_mask, cb_mask)), 'mask.png')
        
                #orig = np.dstack((gray, gray, gray))
                # circle center
                #cv.circle(orig, center, 1, (0, 100, 100), 3)
                # circle outline
                #cv.circle(orig, center, radius, (255, 0, 255), 3)

    def filter_blackframe(self, imgbuf, threshold=0.5):
        thresh = imgbuf.get()[...,1]
        if not np.argmax(thresh>threshold):
            # Below threshold 
            return True
        return False


    def find_reflection(self, imgbuf, debugimg=None):
        # Find reflections in each image
        # Globals
        return
        img_pos = Eval.img_float2byte(original)
        self.pos_map = dict()

        # Iterate and prepare frames
        i = 0
        for frame in imgdata:
            frame = frame[:,:,:1] # Only use red channel
            frame = Eval.img_float2byte(frame)
    
            # Filter
            thresh = cv.threshold(frame, thresh_min, thresh_max, cv.THRESH_BINARY + cv.THRESH_OTSU)[1]
    
            # Find circle contours
            cnts = cv.findContours(thresh, cv.RETR_LIST, cv.CHAIN_APPROX_SIMPLE)
            cnts = cnts[0] if len(cnts) == 2 else cnts[1]
            if len(cnts) == 1:
                # Found reflection
                ((x, y), r) = cv.minEnclosingCircle(cnts[0])
                area = cv.contourArea(cnts[0])
                center = (int(x+0.5),int(y+0.5))
                
                lg.debug(f"Reflection at frame {i}: {center} {area}")
                if DEBUG_SAVE_IMG:
                    cv.circle(img_pos, center, int(r), (0, 0, 255), 2)
                    cv.line(img_pos, center, cb_center, (0,255,0))
                    
                # Calculate spherical coordinates (O = cb_center, I = center reflection)
                OI = (center - cb_center) / cb_radius
                OI[1] *= -1
                lg.debug(f"{OI}")
                pos_map[i] = OI
                #length = np.linalg.norm(OI) / cb_radius
                #phi = np.angle(-OI[1]+OI[0]*1j, deg=True)
                #lg.info(f"{i}: {phi} - {length}")
                ## Calculate angles relative to z axis
                #z = math.sin(length*math.pi/2)
                #lg.info(f">: {z} - {length}")
                    
            elif len(cnts) >1:
                lg.error(f"Frame {i} has {len(cnts)} detected lights, fix threshold / mask.")
                if DEBUG_SAVE_IMG:
                    Eval.img_save(thresh, "threshold.png")
            else:
                lg.warning(f"Warning: Frame {i} has no detected lights.")
            
            # Increment frame counter
            i += 1
        if DEBUG_SAVE_IMG:
            Eval.img_save(img_pos, "positions.png")

    def img_save(img, name):
        if img.dtype != 'uint8':
            lg.debug("Converting image to uint8")
            img = Eval.img_float2byte(img)
            
        file = os.path.join('../HdM_BA/data/eval', name)
        colour.write_image(img, file, 'uint8', method='Imageio')
        
    def img_float2byte(img):
        return (np.clip(img, 0, 1) * 255).astype('uint8')

