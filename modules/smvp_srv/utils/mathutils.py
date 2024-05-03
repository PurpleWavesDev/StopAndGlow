import numpy as np
import math

pi_by_2 = math.pi/2
pi_times_2 = math.pi*2
root_two = math.sqrt(2)

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

def factorial(n: int) -> int:
    """Factorial"""
    if n <= 1:
        return 1
    return n * factorial(n - 1)

def factorial2(n: int) -> int:
    """The double factorial"""
    if n <= 1:
        return 1
    return n * factorial2(n - 2)

