import math
import numpy as np
from enum import Enum

from ..utils import *


class CoordSys(Enum):
    XYZ = 0
    LatLong = 1
    ZVec = 2
    Chromeball = 3
    

class LightPosition:
    def __init__(self, xyz, chromeball=None):
        # 3D coordinates
        self._xyz = xyz
        # Latlong in radians: -pi/2 to +pi/2 Latitute; -pi to +pi Longitude
        self._latlong = None
        # Angles seen from top, -pi to +pi
        self._zvec = None
        # Chromeball uv coordinates (-1 to +1)
        self._chromeball = chromeball
    
    def getXYZ(self):
        return self._xyz
        
    def getLL(self): # Longitude from -pi to +pi
        if self._latlong is None:
            # Calculate Latlong
            latitude = math.asin(self._xyz[2])
            longitude = math.asin(self._xyz[0]/math.cos(latitude)) # -pi/2 to pi/2 front side, zero is middle
            
            # Offsets for longitude
            if self._xyz[1] < 0: # Back side
                longitude = math.pi-longitude # 1/2 * pi to 3/2 * pi
                if longitude > pi_by_2: longitude -= math.tau # Range -pi to +pi
            self._latlong = np.array([latitude, longitude], dtype=np.float32)
            
        return self._latlong
    
    def getZVec(self):
        """2D Vector vec around zenith with max length PI"""
        if self._zvec is None:
            if self._xyz == [0,0,1]:
                self._zvec = np.array([0,0], dtype=np.float32)
            elif self._xyz == [0,0,-1]:
                self._zvec = np.array([math.pi,0], dtype=np.float32) # Could be any point on the circle with radius pi
            else:
                # Vector around 0,0 with direction of xz-plane (longitude) and length of angle from zenith
                self._zvec = np.array([self._xyz[0], self._xyz[1]], dtype=np.float32)
                self._zvec /= math.sqrt(self._zvec[0]**2 + self._zvec[2]**2) # Normalize
                self._zvec *= math.acos(self._xyz[2]) # Range 0 to pi (zenith is 0)
                #alt_angle = self._zvec * (1-np.dot(self._xyz, [0,0,1]))/2 * math.pi # Alternative calculation
        return self._zvec
    
    def getLLNorm(self) -> [float, float]:
        """Returns Lat-Long coordinates in the range of -1 to 1"""
        ll = self.getLL()
        return np.array([ll[0] / pi_by_2, ll[1] / math.pi], dtype=np.float32)

    def getZVecNorm(self) -> [float, float]:
        """Returns Zenith Angle with max length 1"""
        return self.getZVec() / math.pi
    
    def getChromeball(self) -> [float, float]:
        return self._chromeball
    
    def get(self, coords: CoordSys, normalized=False):
        match coords:
            case CoordSys.XYZ:
                return self.getXYZ()
            case CoordSys.LatLong:
                if normalized:
                    return self.getLLNorm()
                return self.getLL()
            case CoordSys.ZVec:
                if normalized:
                    return self.getTopAnglesNorm()
                return self.getTopAngles()
            case CoordSys.Chromeball:
                return self.getChromeball()
    
    def __str__(self):
        return str(self._xyz)

    ### Static functions ###
    
    def FromMirrorball(uv, viewing_angle_by_2=0) -> "LightPosition":
        uv=np.array(uv)
        # First get the length of the UV coordinates
        length = np.linalg.norm(uv)
        uv_norm = uv/length
        
        # Get direction of light source
        vec = np.array([0,1,0]) # Vector pointing into camera
        axis = np.array([-uv_norm[1],0,uv_norm[0]]) # Rotation axis that is the direction of the reflection rotated 90° on Z
        theta = math.asin(length)*2 # Calculate the angle to the reflection which is two times the angle of the normal on the sphere
        theta_corrected = theta / np.pi * (np.pi-viewing_angle_by_2) # Perspective correction: New range is to 180° - viewing_angle/2
        vec = np.dot(RotationMatrix(axis, theta_corrected), vec) # Rotate vector to light source
        
        return LightPosition(vec, chromeball=uv)

    def FromLatLong(ll, normalized=False) -> "LightPosition":
        if normalized:
            # 'De'normalize
            ll = np.array([ll[0]*pi_by_2, ll[1]*math.pi], dtype=np.float32)
        # Calculate XYZ vector
        xz_length = math.cos(ll[0])
        xyz = np.array([xz_length * math.sin(ll[1]), xz_length * math.cos(ll[1]), math.sin(ll[0])], dtype=np.float32)
        
        # LP object with LatLong vector
        lp = LightPosition(xyz)
        lp._ll = ll
        return lp

