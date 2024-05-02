import math
import numpy as np
import taichi as ti
import taichi.math as tm
from enum import Enum

from ..utils import *


class CoordSys(Enum):
    XYZ = 0
    LatLong = 1
    ZVec = 2
    Chromeball = 3
    

@ti.data_oriented
class LightPosition:
    def __init__(self, xyz, chromeball=None):
        # 3D coordinates
        self._xyz = ti.Vector([xyz[0], xyz[1], xyz[2]], dt=ti.f32)
        # Latlong in radians: -pi/2 to +pi/2 Latitute; -pi to +pi Longitude
        self._latlong = None
        # Angles seen from top, -pi to +pi
        self._zvec = None
        # Chromeball uv coordinates (-1 to +1)
        self._chromeball = chromeball
    
    def getXYZ(self) -> [float, float, float]:
        return self._xyz
    
    def getLL(self) -> [float, float]:
        """Returns Lat-Long coordinates in the range of -Pi/2 to +Pi/2 for Latitude and -Pi to +Pi for Longitude"""
        if self._latlong is None:
            lp = LightPosTi(xyz=self._xyz)
            self._latlong = lp.getLL()
        return self._latlong
    
    def getZVec(self) -> [float, float]:
        """2D Vector vec around zenith with max length PI"""
        if self._zvec is None:
            lp = LightPosTi(xyz=self._xyz)
            self._zvec = lp.getZVec()
        return self._zvec
    
    def getLLNorm(self) -> [float, float]:
        """Returns Lat-Long coordinates in the range of -1 to 1"""
        ll = self.getLL()
        return [ll[0] / pi_by_2, ll[1] / tm.pi]

    def getZVecNorm(self) -> [float, float]:
        """Returns Zenith Angle with max length 1"""
        return self.getZVec() / tm.pi
#    
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
                    return self.getZVecNorm()
                return self.getZVec()
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
        vec = np.array([0,-1,0]) # Vector pointing into camera
        axis = np.array([-uv_norm[1],0,uv_norm[0]]) # Rotation axis that is the direction of the reflection rotated 90° on Y
        theta = math.asin(length)*2 # Calculate the angle to the reflection which is two times the angle of the normal on the sphere
        theta_corrected = theta / np.pi * (np.pi-viewing_angle_by_2) # Perspective correction: New range is to 180° - viewing_angle/2
        vec = np.dot(RotationMatrix(axis, theta_corrected), vec) # Rotate vector to light source
        
        return LightPosition(vec, chromeball=uv)

    def FromLatLong(ll, normalized=False) -> "LightPosition":
        # LP object with LatLong vector
        lp = LightPosition(LightPosTi().FromLL(ll, normalized).xyz)
        lp._ll = ll
        return lp

@ti.dataclass
class LightPosTi:
    xyz: tm.vec3
    
    @ti.pyfunc
    def getLL(self):
        """Returns Lat-Long coordinates in the range of -Pi/2 to +Pi/2 for Latitude and -Pi to +Pi for Longitude"""
        # Calculate Latlong
        latitude = tm.asin(self.xyz[2])
        longitude = tm.asin(self.xyz[0]/tm.cos(latitude)) # -pi/2 to pi/2 front side, zero is middle
        
        # Offsets for longitude
        if self.xyz[1] > 0: # Back side
            longitude = tm.pi-longitude # 1/2 * pi to 3/2 * pi
            if longitude > tm.pi: longitude -= pi_times_2 # Range -pi to +pi
        return ti.Vector([latitude, longitude], dt=ti.f32)
    
    @ti.pyfunc
    def getZVec(self):
        """2D Vector vec around zenith with directions in X and Y and max length of PI"""
        zvec = ti.Vector([self.xyz[0], self.xyz[1]], dt=ti.f32)
        if self.xyz[2] == 1.0:
            zvec = ti.Vector([0,0], dt=ti.f32)
        elif self.xyz[2] == -1.0:
            zvec = ti.Vector([0,tm.pi], dt=ti.f32) # Could be any point on the circle with radius pi
        else:
            # Vector around 0,0 with direction of xy-plane (longitude) and length of angle from zenith
            zvec /= tm.sqrt(zvec[0]**2 + zvec[1]**2) # Normalize
            zvec *= tm.acos(self.xyz[2]) # Range 0 to pi (zenith is 0
            #alt_angle = zvec * (1-np.dot(self.xyz, [0,0,1]))/2 * tm.pi # Alternative calculation
        return zvec
    
    @ti.pyfunc
    def getLLNorm(self):
        """Returns Lat-Long coordinates in the range of -1 to 1"""
        lat, long = self.getLL()
        return ti.Vector([lat / pi_by_2, long / tm.pi], dt=ti.f32)

    @ti.pyfunc
    def getZVecNorm(self):
        """Returns Zenith Angle with max length 1"""
        return self.getZVec() / tm.pi
    
    @ti.pyfunc
    def FromLL(self, ll, normalized=False):
        if normalized:
            # 'De'normalize
            ll = ti.Vector([ll[0]*pi_by_2, ll[1]*tm.pi], dt=ti.f32)
        # Calculate XYZ vector
        xy_length = tm.cos(ll[0])
        self.xyz = ti.Vector([xy_length * math.sin(ll[1]), -xy_length * math.cos(ll[1]), math.sin(ll[0])], dt=ti.f32)
        return self
    
    @ti.pyfunc
    def ZVec2LL(self, zvec, normalized=False):
        """Returns LatLong from ZVec in the range of -Pi/2 to +Pi/2 for Latitude and -Pi to +Pi for Longitude"""
        # Denormalize
        coords = ti.Vector([zvec[0], zvec[1]], dt=ti.f32)
        if normalized:
            coords = ti.Vector([zvec[0]*tm.pi, zvec[1]*tm.pi], dt=ti.f32)
        
        # Latitude is length of vector, max pi
        lat = tm.min(ti.sqrt(coords[0]**2 + coords[1]**2), tm.pi) # Range 0 to +Pi, correct later
        
        # Longitude is direction of vector
        long = 0.0
        if lat > 0:
            # arctan y/x where x points towards camera, y to the right -> x is -coords[0] (points away from cam), y is coords[1] (points to the right)
            long = tm.atan2(-coords[0], coords[1]) # Range -Pi to +Pi TODO check order again
        
        return ti.Vector([lat-pi_by_2, long], dt=ti.f32) # Offset for Latitude
    
    @ti.pyfunc
    def ZVec2LLNorm(self, zvec, normalized=False): # TODO Copy implementation and adapt for normalized
        """Returns LatLong from ZVec in the range of -1 to +1"""
        lat, long = self.ZVec2LL(zvec, normalized)
        return ti.Vector([lat / pi_by_2, long / tm.pi], dt=ti.f32)
    
    @ti.pyfunc
    def LL2ZVec(self, ll, normalized=False):
        """Returns the Zenith Vector from LatLong in the range of -Pi to +Pi"""
        lat, long = ll
        if normalized:
            # 'De'normalize
            lat = lat * pi_by_2
            long = long * tm.pi

        length = pi_by_2-lat
        return ti.Vector([length * tm.sin(long), -length * tm.cos(long)], dt=ti.f32)
        
    
    @ti.pyfunc
    def LL2ZVecNorm(self, ll, normalized=False): # TODO Copy implementation and adapt for normalized
        """Returns the Zenith Vector from LatLong in the range of -1 to +1"""
        return self.LL2ZVec(ll, normalized) / tm.pi
