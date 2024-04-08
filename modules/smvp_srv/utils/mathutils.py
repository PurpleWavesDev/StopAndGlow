import numpy as np
import math


def NormalizeLatlong(latlong) -> [float, float]:
    """Returns Lat-Long coordinates in the range of 0 to 1"""
    return ((latlong[0]+90) / 180, (latlong[1]+180)%360 / 360)

def LatlongRadians(latlong) -> [float, float]:
    """Returns Lat-Long coordinates as radians in the range of -Pi/2 to Pi/2 Latitude and -Pi to Pi Longitude"""
    return (math.radians(latlong[0]), math.radians(latlong[1]))


def RotationMatrix(axis, theta):
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
