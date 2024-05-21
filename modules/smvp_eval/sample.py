# Imports and data loading
from ..smvp_srv.data import *
import numpy as np
import scipy


# Data sampling
def sampleSeqData(lp_sequence, pix, rotation_steps=0):
    # Create the mesh in polar coordinates and compute corresponding Z.
    x = np.zeros((0, ))
    y = np.zeros((0, ))
    z = np.ones((0, ))

    for _, img, lp in lp_sequence:
        ll = lp.getLL()
        lp_rot = LightPosition.FromLatLong([ll[0], ll[1]+rotation_steps*pi_by_2])
        x = np.append(x, [lp_rot.getZVecNorm()[0]])
        y = np.append(y, [lp_rot.getZVecNorm()[1]])
        z = np.append(z, [img.getPix(pix).lum().get()]) # asDomain(ImgDomain.sRGB, no_taich=True)
        
    return x, y, z

def sampleRtiData(fn, calibration, coord_system, rotation_steps=0):
    # Create the mesh in polar coordinates and compute corresponding Z.
    x = np.zeros((0, ))
    y = np.zeros((0, ))
    z = np.ones((0, ))
    
    for _, lp in calibration:
        ll = lp.getLL()
        lp_rot = LightPosition.FromLatLong([ll[0], ll[1]+rotation_steps*pi_by_2])
        x = np.append(x, [lp_rot.getZVecNorm()[0]])
        y = np.append(y, [lp_rot.getZVecNorm()[1]])
        # Fill arrays with coords and samples
        match coord_system:
            case CoordSys.LatLong:
                z = np.append(z, [fn(lp.getLLNorm())])
            case CoordSys.ZVec:
                z = np.append(z, [fn(lp.getZVecNorm())])
            case CoordSys.XYZ:
                z = np.append(z, [fn(lp.getXYZ())])
        
    return x, y, z



## Define RTI fitter functions
from modules.smvp_srv.processing.fitter.spherical import *

# General PTM function
def calcPtm(coord, pix, seq):
    u, v = coord
    
    # 1.0 + lat + long
    val = seq[0].getPix(pix).lum().get() +\
    seq[1].getPix(pix).lum().get() * u
    seq[2].getPix(pix).lum().get() * v

    # Higher degrees
    idx = 3
    for n in range(2, 6+1): # 6 is max degree
        if idx >= len(seq):
            break
        
        for i in range(n+1):
            val += u**(n-i) * v**i * seq[idx].getPix(pix).lum().get()
            idx += 1
    
    return val

# Spherical Harmonics
def calcShm(coord, pix, seq):
    #x,y,z = coord
    lat, long = coord
    val = 0
    for i in range(len(seq)):
        l = math.floor(math.sqrt(i))
        m = i - l * (l + 1)
        # l & m are parameters of the degree of the harmonics in the shape of:
        # (0,0), (1,-1), (1,0), (1,1), (2,-2), (2,-1), ...
        #line[coeff_num] = SHFitter.SH(l, m, u, v)
        #val += SHFitter.SHHardCoded(l, m, x, y, z) * seq[i].getPix(pix).lum().get()
        val += scipy.special.sph_harm(m, l, long*np.pi + (pi_by_2 if m < 0 else 0), pi_by_2 - lat*pi_by_2).real * seq[i].getPix(pix).lum().get()
        
    return val


## Define RTI Plotter

def sampleRtiGridData(fn, coord_system, rotation_steps=0, resolution=80):
    # Create the mesh in polar coordinates and compute corresponding Z.
    range_lat = np.linspace(1.0, -1.0, resolution, endpoint=False) # Normalized -np.pi/2, np.pi/2
    range_long = np.linspace(1.0, -1.0, resolution) # Normalized -np.pi, np.pi
    LAT, LONG = np.meshgrid(range_lat, range_long) # First is radius and repeats, second is same in whole array
    Z = np.empty((0, ))
    
    def getSampleArray(lat_arr, long_arr):
        samples = np.empty((0,))
        for ll in zip(lat_arr, long_arr):
            match coord_system:
                case CoordSys.LatLong:
                    samples = np.append(samples, fn(ll))
                case CoordSys.ZVec:
                    samples = np.append(samples, fn(LightPosition.FromLatLong(ll, normalized=True).getZVecNorm()))
                case CoordSys.XYZ:
                    samples = np.append(samples, fn(LightPosition.FromLatLong(ll, normalized=True).getXYZ()))
        return samples

    for lat, long in zip(LAT, LONG):
        if Z.shape == (0,):
            Z = getSampleArray(lat, long)
        else:
            Z = np.vstack((Z, getSampleArray(lat, long)))
        
    # Express the mesh in the cartesian system.
    X, Y = (-LAT+1)/2*np.sin(LONG*np.pi + rotation_steps*pi_by_2), -(-LAT+1)/2*np.cos(LONG*np.pi + rotation_steps*pi_by_2)
    return X, Y, Z
    

