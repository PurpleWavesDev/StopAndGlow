import logging as log
import numpy as np
import math

import cv2 as cv
from PIL import Image

from src.imgdata import *
from src.config import Config

class Eval:
    def __init__(self):
        # Settings
        self.thresh_min=100
        self.thresh_max=255

    # Find center and radius of chromeball
    def find_center(self, imgdata):
        frame = imgdata.get(0, delete=True)
        cb_center = (0,0)
        cb_radius = 0

        # use red channel only
        cb_mask = (frame[...,1] * 255).astype('uint8')

        gray = cb_mask
        #cv.medianBlur(mask, 5)

        #cv.Smooth(orig, orig, cv.CV_GAUSSIAN, 5, 5)
        #cv.CvtColor(orig, grey_scale, cv.CV_RGB2GRAY)
        #cv.Erode(grey_scale, processed, None, 10)
        #cv.Dilate(processed, processed, None, 10)
        #cv.Canny(processed, processed, 5, 70, 3)
        #cv.Smooth(processed, processed, cv.CV_GAUSSIAN, 15, 15)
            
        rows = gray.shape[0]
        circles = cv.HoughCircles(gray, cv.HOUGH_GRADIENT, 1, rows / 8,
                                    param1=100, param2=30,
                                    minRadius=100, maxRadius=1080)
                
        if circles is not None:
            circles = np.uint16(np.around(circles))
            for i in circles[0, :]:
                cb_center = np.array((i[0], i[1]))
                cb_radius = i[2]
                    
                #orig = np.dstack((gray, gray, gray))
                # circle center
                #cv.circle(orig, center, 1, (0, 100, 100), 3)
                # circle outline
                #cv.circle(orig, center, radius, (255, 0, 255), 3)

    def filter_blackframes(self, imgdata, threshold=0.1):
        pass

    def find_reflections(self, imgdata):
        # Find reflections in each image
        # Globals
        img_pos = img_float2byte(original)
        self.pos_map = dict()

        # Iterate and prepare frames
        i = 0
        for frame in imgdata:
            frame = frame[:,:,:1] # Only use red channel
            frame = img_float2byte(frame)
    
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
                    img_save(thresh, "threshold.png")
            else:
                lg.warning(f"Warning: Frame {i} has no detected lights.")
            
            # Increment frame counter
            i += 1
        if DEBUG_SAVE_IMG:
            img_save(img_pos, "positions.png")

    def img_save(img, name):
        if img.dtype != 'uint8':
            lg.debug("Converting image to uint8")
            img = img_float2byte(img)
            
        file = os.path.join(OUTPUT_PATH, name)
        colour.write_image(img, file, 'uint8', method='Imageio')
        
    def img_float2byte(img):
        return (np.clip(img, 0, 1) * 255).astype('uint8')

