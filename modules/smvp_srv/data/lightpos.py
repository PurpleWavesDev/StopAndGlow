import math
import numpy as np
from enum import Enum

from ..utils import *


class CoordType(Enum):
    XYZ = 0
    LatLong = 1
    ZVec = 2
    Chromeball = 3
    

class LightPosition:
    def __init__(self, xyz, chromeball=None):
        # 3D coordinates
        self._xyz = xyz
        # Latlong in radians: -pi to +pi Latitute; 0 to 2pi Longitude
        self._latlong = None
        # Angles seen from top, -pi to +pi
        self._zvec = None
        # Chromeball uv coordinates (-1 to +1)
        self._chromeball = chromeball
    
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
            self._latlong = np.array([latitude, (longitude+pi_times_2) % pi_times_2], dtype=np.float32) # make longitude all positive
            
        return self._latlong
    
    def getZVec(self):
        """2D Vector vec around zenith with max length PI"""
        if self._zvec is None:
            if self._xyz == [0,1,0]:
                self._zvec = np.array([0,0], dtype=np.float32)
            elif self._xyz == [0,-1,0]:
                self._zvec = np.array([math.pi,0], dtype=np.float32) # Could be any point on the circle with radius pi
            else:
                # Vector around 0,0 with direction of xz-plane (longitude) and length of angle from zenith
                self._zvec = np.array([self._xyz[0], self._xyz[2]], dtype=np.float32)
                self._zvec /= math.sqrt(self._zvec[0]**2 + self._zvec[1]**2) # Normalize
                self._zvec *= math.acos(self._xyz[1]) # Range 0 to pi (zenith is 0)
                #alt_angle = self._zvec * (1-np.dot(self._xyz, [0,1,0]))/2 * math.pi # Alternative calculation
        return self._zvec
    
    def getLLNorm(self) -> [float, float]:
        """Returns Lat-Long coordinates in the range of 0 to 1"""
        ll = self.getLL()
        return np.array([(ll[0]+pi_by_2) / math.pi, (ll[1]+math.pi) % pi_times_2 / pi_times_2], dtype=np.float32)

    def getZVecNorm(self) -> [float, float]:
        """Returns Zenith Angle with max length 1"""
        return self.getZVec() / math.pi
    
    def getChromeball(self) -> [float, float]:
        return self._chromeball
    
    def get(self, coords: CoordType, normalized=False):
        match coords:
            case CoordType.XYZ:
                return self.getXYZ()
            case CoordType.LatLong:
                if normalized:
                    return self.getLLNorm()
                return self.getLL()
            case CoordType.ZVec:
                if normalized:
                    return self.getTopAnglesNorm()
                return self.getTopAngles()
            case CoordType.Chromeball:
                return self.getChromeball()

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
        vec = np.dot(RotationMatrix(axis, theta_corrected), vec) # Rotate vector to light source
        
        return LightPosition(vec, chromeball=uv)

