import logging as log
import random
import numpy as np
import math

import cv2 as cv

from ..data import *
from ..hw import *


class LightCtl:
    def __init__(self, hw = None):
        self.img_res_base = 1000
        self.img_background = 10
        self.blur_size = 15
        self._lightVals = dict()
        if hw is not None:
            self.setHw(hw)
    
    def setHw(self, hw):
        self._cal = hw.cal
        self._lights = hw.lights
        self._lightVals.clear()
        return # TODO
        
        # Init (ti?) fields
        light_count = len(self._cal)
        
        # Light info: idx, id, latlong, 6x (neighbour idx, neighbour distance), distance_from_sample
        self._light_ids = []
        section_begin = [0] * LightCtl.GetSectionCount()+1
        for section in range(LightCtl.GetSectionCount()):
            section_begin[section] = len(self._light_ids)
            for light in self._cal:
                if GetSection(light['latlong']) == section:
                    self._light_ids.append(light['id'])
        # Last section begin is end of array
        section_begin[-1] = len(self._light_ids)
        
        # Find 6 closest neighbours and assign IDs (2 above, 2 even, 2 below)
        for id in self._light_ids:
            latlong = self._cal[id]['latlong']
            section = LightCtl.GetSection(latlong)
            # Check lights in section and neigbouring sections for distances
            for neigbour_section in LightCtl.GetNeigbouringSections():
                for neighbour_light in self.getLightsInSection(neigbour_section):
                    neigh_latlong = 0
                    dist = LightCtl.GetDistanceOnSphere()
                    latlong_diff = latlong-neigh_latlong
                    if latlong_diff[0] > 10: # Above
                        pass
                    elif latlong_diff[0] < -10: # Below
                        pass
                    else: # Same height
                        pass
    
    def getLightsInSection(self, section):
        return self._light_ids[range(section_begin[section], section_begin[section+1])]
            
    # Divide and conquer - Sort lights into sections of dome
    def GetSection(latlong) -> int:
        # 0: lat > 60°; 1-4: lat > 30°, long in 90° steps; 5-12: lat > 0°, long in 45° steps; 13-20: lat <= 0°, long in 45° steps
        # Section for latitude
        section = [0, 1, 5, 13][max(90-latlong[0]//30, 3)] 
        # Add sections for latitude rings that are separated
        if section == 1:
            section += latlong[0] // 90
        elif section == 5 or section == 13:
            section += latlong[0] // 45
                
    def GetSectionCount() -> int:
        return 21
        
    def GetNeigbouringSections(section) -> list:
        if section == 0:
            return list(range(1, 5))
        elif section <=4: # Section from 1-4
            left = section-1 if section != 1 else 4
            right = section+1 if section != 4 else 1
            lower = 5+2*(section-1)
            lower_left = lower-1 if section != 1 else 12
            lower_right = lower+2 if section != 4 else 5
            return (0, left, right, lower_left, lower, lower+1, lower_right)
        elif section <= 12: # Section from 5-12
            upper = (section-5)/2 + 1
            upper_left = int(upper-0.5)
            upper_right = int(upper+0.5)
            if upper_left == 0: upper_left = 4
            elif upper_right == 5: upper_right = 1
            left = section-1 if section != 5 else 12
            right = section+1 if section != 12 else 5
            return (upper_left, upper_right, left, right, left+8, section+8, right+8)
        else: # Section from 13-20
            left = section-1 if section != 13 else 20
            right = section+1 if section != 20 else 13
            return (left-8, section-8, right-8, left, right)
    
    def GetDistanceDirect(latlong1, latlong2):
        lat1 = math.radians(latlong1[0])
        lat2 = math.radians(latlong2[0])
        long_diff = math.radians(latlong1[1]-latlong2[1])
        return math.sqrt(2 - 2 * (math.sin(lat1)*math.sin(lat2) * cos(long_diff) + math.cos(lat1)*math.cos(lat2)))
    
    def GetDistanceOnSphere(latlong1, latlong2):
        lat1 = math.radians(latlong1[0])
        lat2 = math.radians(latlong2[0])
        long_diff = math.radians(latlong1[1]-latlong2[1])
        
        a = 0.5 - cos(lat2-lat1)/2 + cos(lat1)*cos(lat2) * (1-cos(long_diff))/2
        return 2 * math.asin(math.sqrt(a))
    
    def processHdri(self, hdri: ImgBuffer, exposure_correction=1):
        res_y, res_x = hdri.get().shape[:2]
        blur_size = int(self.blur_size*res_y/100)
        blur_size += 1-blur_size%2 # Make it odd
        
        # Blur HDRI to reduce errors
        # TODO: Conversion lin->srgb->blur->lin reduces extremes but they are probably necessary for accurate light energy?
        #hdri = hdri.asDomain(ImgDomain.sRGB)
        self._processed_hdri = ImgBuffer(img=cv.GaussianBlur(hdri.get(), (blur_size, blur_size), -1))
        #hdri = hdri.asDomain(ImgDomain.Lin) # Conversion back
        

    ### Functions for samling light values ###

    def sampleHdri(self, longitude_offset=0):
        res_y, res_x = self._processed_hdri.get().shape[:2]
        for light in self._cal:
            # Sample point in HDRI
            latlong = light['latlong']
            x = int(res_x * (360 - (latlong[1]+longitude_offset) % 360) / 360.0) # TODO: Is round here wrong? Indexing error when rounding up on last value!
            y = int(round(res_y/2 - res_y * latlong[0]/180.0))
            self._lightVals[light['id']] = self._processed_hdri[x, y]
    
    def sampleWithUV(self, f):
        for light in self._cal:
            sample = f(light['uv'])
            self._lightVals[light['id']] = sample
    
    def sampleWithLatLong(self, f):
        for light in self._cal:
            sample = f(light['latlong'])
            self._lightVals[light['id']] = sample

    # TODO!
    #def getLightDict(self, domain=ImgDomain.Lin, as_int=True):
    #    if as_int:
    #        return [light.asDomain(domain).asInt().get()]
    def getLights(self):
        return self._lightVals

    def writeLights(self):
        self._lights.setLights(self._lightVals)
        self._lights.write()

    ### Light functions ###

    def setTop(self, latitude = 60, brightness = DMX_MAX_VALUE):
        # Sample lights
        self.sampleWithLatLong(lambda latlong: ImgBuffer.FromPix(brightness) if latlong[0] > latitude else ImgBuffer.FromPix(0))
        # Write DMX values
        self.writeLights()
    
    def setRing(self, latitude = 45, ring_width = 15, brightness = DMX_MAX_VALUE):
        # Sample lights
        self.sampleWithLatLong(lambda latlong: ImgBuffer.FromPix(brightness) if latlong[0] > latitude and latlong[0] < latitude+ring_width else ImgBuffer.FromPix(0))
        # Write DMX values
        self.writeLights()
    
    def setNth(self, nth, brightness = DMX_MAX_VALUE):
        random.seed()
        self._lights.reset()
        for light in self._cal:
            if random.randrange(0, nth) == 0:
                self._lightVals[light['id']] = ImgBuffer.FromPix(brightness)
        self.writeLights()
        #self._mask = [light['id'] for i, light in enumerate(self._cal) if i % nth == 0] # TODO: This way every nth is lit and not random
    
    #TODO: Move to renderer
    def generateLightingFromSequence(self, img_seq: Sequence, longitude_offset=0) -> ImgBuffer:
        # Hier kannst du einsteigen, Iris :)
        # img_seq: Alle Bilder der einzelnen Lampen
        # self._processed_hdri: geblurtes HDRI

        generated = ImgBuffer(domain=ImgDomain.Lin)
        res_y, res_x = self._processed_hdri.get().shape[:2]

        for id, img in img_seq:
            # Test if calibration entry is valid -> configuration might be incomplete!

            if self._cal[id] is not None:
                # ID ist Lampen ID, entspricht der ID der calibration
                latlong = self._cal[id]['latlong'] # -> Koordinaten der Lampe
                img = img.asDomain(ImgDomain.Lin, as_float=True) # -> Bild als Linear

                # HDRI sampling
                x = int(res_x * (360 - (latlong[1]+longitude_offset) % 360) / 360.0) # TODO: Is round here wrong? Indexing error when rounding up on last value!
                y = int(round(res_y/2 - res_y * latlong[0]/180.0))
                rgb_factor = self._processed_hdri[x, y]

                if not generated.hasImg():
                    generated.set(img.get() * rgb_factor.get())
                else:
                    generated.set(generated.get() + img.get() * rgb_factor.get())

        generated.set(generated.get() / len(img_seq)) # Normalize brightness
        return generated # Frame wird returned und in domectl.py gespeichert


    ### Functions to generate images with mapping of sampled lights ###
    
    def generateUVMapping(self, image=None) -> ImgBuffer:
        # Generate RGB image and draw blue circle for sphere
        res = self.img_res_base
        if image is None:
            image = ImgBuffer(img=np.full((res, res, 3), self.img_background, dtype='uint8'), domain=ImgDomain.sRGB)
        else:
            image = image.asDomain(ImgDomain.sRGB).asInt()
            res = min(image.get().shape[:2])
        res_2 = int(round(res/2))
        
        # Draw sphere contour
        cv.circle(image.get(), (res_2, res_2), res_2, (0, 0, 255), 2)
        light_radius = 6 # TODO: Calculate
        
        for light_entry in self._cal:
            value = self._lightVals[light_entry['id']].asDomain(ImgDomain.sRGB).asInt().get()[0][0].tolist() if not None else (0)
            x = int(round(res_2 + res_2*light_entry['uv'][0]))
            y = int(round(res_2 - res_2*light_entry['uv'][1]))
            # Fill
            cv.circle(image.get(), (x, y), light_radius, value, cv.FILLED)
            # Outline
            cv.circle(image.get(), (x, y), light_radius, (255, 255, 255), 1)
            
        return image
        
    def generateLatLongMapping(self, image=None) -> ImgBuffer:
        # Generate RGB image with aspect ratio 2:1
        res_x, res_y = (self.img_res_base * 2, self.img_res_base)
        if image is None:
            image = ImgBuffer(img=np.full((res_y, res_x, 3), self.img_background, dtype='uint8'), domain=ImgDomain.sRGB)
        else:
            image = image.asDomain(ImgDomain.sRGB).asInt()
            res_y, res_x = image.get().shape[:2]
        light_radius = 6 # TODO: Calculate
        
        # Draw lights as circles with fill
        for light_entry in self._cal:
            value = self._lightVals[light_entry['id']].asDomain(ImgDomain.sRGB).asInt().get()[0][0].tolist() if not None else (0)
            x = int(round(res_x * light_entry['latlong'][1] / 360))
            y = int(round(res_y/2 - (res_y/2) * light_entry['latlong'][0] / 90))
            # Fill
            cv.circle(image.get(), (x, y), light_radius, value, cv.FILLED) # TODO value is gray or RGB sometimes
            # Outline
            cv.circle(image.get(), (x, y), light_radius, (255, 255, 255), 1)

        return image

        