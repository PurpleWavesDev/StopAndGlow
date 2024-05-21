# Imports and data loading
from ..smvp_srv.data import *

import numpy as np

# Axes3D import has side effects, it enables using projection='3d' in add_subplot
from mpl_toolkits.mplot3d import Axes3D  
import matplotlib.pyplot as plt
import matplotlib as mpl


## Define Data Plotter with coords from calibration

# Polar plot where top lights are in center
def plotData(data, trisurf, normalize=True, clip=True, trisurf_small=False, ax=None, title=None):
    if ax is None:
        fig = plt.figure()
        ax = fig.add_subplot(projection='3d')
    if title is not None:
        ax.set_title(title)
    
    x, y, z = data
    
    # Normalize
    z_max = np.max(z) if isinstance(normalize, bool) else normalize
    z_offset = -1.3 if normalize == True else -1.3 * z_max
    z_lim_max = 1.0 if normalize == True else z_max
    # Normalize & clip
    if isinstance(normalize, bool) and normalize is True:
        z = z / z_max
    if clip:
        z = np.clip(z, 0, None)
        z_maxclip = np.clip(z, None, z_lim_max)
        
    if trisurf:
        # Plot the surface.
        ax.plot_trisurf(x, y, z_maxclip, vmin=z.min()*2, cmap=plt.cm.YlGnBu_r, antialiased=True, norm=mpl.colors.Normalize(vmin=0, vmax=z_max, clip=False))

        # Plot projections of the contour
        ax.tricontourf(x, y, z, zdir='z', offset=z_offset, cmap=plt.cm.coolwarm)

        # Set limits and add labels
        xy_lims = (-1.2, 1.2) if trisurf_small else (-0.8, 0.8)
        ax.set(xlim=xy_lims, ylim=xy_lims, zlim=(z_offset, z_lim_max),\
            xlabel='X', ylabel='Y', zlabel='Z')
    else:
        # Same as above
        ax.plot_surface(x, y, z_maxclip, cmap=plt.cm.YlGnBu_r, antialiased=True, norm=mpl.colors.Normalize(vmin=0, vmax=z_max, clip=False))
        ax.contourf(x, y, z, zdir='z', offset=z_offset, cmap='coolwarm')
        ax.set(xlim=(-1.2, 1.2), ylim=(-1.2, 1.2), zlim=(z_offset, z_lim_max),\
            xlabel='X', ylabel='Y', zlabel='Z')

def plotGridData(data, normalize=True, clip=True, ax=None, title=None):
    plotData(data, False, normalize, clip, False, ax, title)
def plotPointData(data, normalize=True, clip=True, trisurf_small=False, ax=None, title=None):
    plotData(data, True, normalize, clip, trisurf_small, ax, title)