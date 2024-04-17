import math
import numpy as np

from ..utils import *

pi_by_2 = math.pi/2
pi_times_2 = math.pi*2

class LightPosition:
    def __init__(self, xyz):
        
        self._xyz = xyz
        # Latlong in degrees: -180° to 180° Latitute, 0-360° Longitude
        self._latlong = None
        # Angles 
        self._zangle = None
    
    def getXYZ(self):
        return self._xyz
        
    def getLL(self):
        if self._latlong is None:
            # Calculate Latlong
            latitude = math.asin(self._xyz[1])
            longitude = pi_by_2 - math.acos(self._xyz[0]/math.cos(latitude)) # -pi/2 to pi/2 front side
            
            # Offsets for longitude
            if self._xyz[2] < 0: # Back side
                longitude = (math.pi-longitude) # pi/2 to 3* pi/2, correct value
            self._latlong = [latitude, (longitude+360) % 360] # make longitude all positive
            
        return self._latlong
    
    def getZAngles(self): # TODO: Name? Vertikalwinkel/Höhenwinkel/Zenitwinkel
        """Angles around X and Y axis where the zenith is (0, 0)"""
        if self._zangle is None:
            if self._xyz[1] > 0:
                # Calculate
                angle1 = math.asin(self._xyz[2]) # Orthogonal of screen
                angle2 = math.asin(self._xyz[0]) # Horizontal component
                self._zangle = [angle1, angle2]
            else:
                # Lower part of sphere
                angle1 = pi_by_2 + math.acos(self._xyz[2]) if self._xyz[2] > 0 else -pi_by_2 - math.acos(math.abs(self._xyz[2]))
                angle2 = pi_by_2 + math.acos(self._xyz[0]) if self._xyz[0] > 0 else -pi_by_2 - math.acos(math.abs(self._xyz[0]))
                self._zangle = [angle1, angle2]
        return self._zangle
    
    def getLLNorm(self) -> [float, float]:
        """Returns Lat-Long coordinates in the range of 0 to 1"""
        ll = self.getLL()
        return [(ll[0]+90) / math.pi, (ll[1]+math.pi) % pi_times_2 / pi_times_2]

    def getZAnglesNorm(self) -> [float, float]:
        """Returns Zenith Angle from -1 to 1"""
        return self.getZAngles() / math.pi

    ### Static functions ###
    
    def MirrorballToCoordinates(uv, viewing_angle_by_2=0) -> "LightPosition":
        uv=np.array(uv)
        # First get the length of the UV coordinates
        length = np.linalg.norm(uv)
        uv_norm = uv/length
        
        # Get direction of light source
        vec = np.array([0,0,1]) # Vector pointing into camera
        axis = np.array([-uv_norm[1],uv_norm[0],0]) # Rotation axis that is the direction of the reflection rotated 90° on Z
        theta = math.asin(length)*2 # Calculate the angle to the reflection which is two times the angle of the normal on the sphere
        theta_corrected = theta / np.pi * (np.pi-viewing_angle_by_2) # Perspective correction: New range is to 180° - viewing_angle/2
        vec = np.dot(mutils.RotationMatrix(axis, theta_corrected), vec) # Rotate vector to light source
        
        return LightPosition(vec)

