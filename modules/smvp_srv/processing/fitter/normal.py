from .pseudoinverse import PseudoinverseFitter
from ...hw.calibration import *

import taichi as ti
import taichi.math as tm
import taichi.types as tt
from ...utils import ti_base as tib

class NormalFitter(PseudoinverseFitter):
    name = "Normalmap Fitter"
    
    def __init__(self, settings = {}):
        super().__init__(settings)
        self._settings['rgb'] = False
        # Settings
        #self._scale_positive = settings['scale_to_positive'] if 'scale_to_positive' in settings else True
    
    def getCoefficientCount(self) -> int:
        """Returns number of coefficients"""
        return 3
            
    def fillLightMatrix(self, line, lightpos: LightPosition):
        line = lightpos.getXYZ()
    
"""
# bilder und lichter laden 
images= []
light_directions = []

# bilder des frame sets in graustufenbilder (nach luminanz) wandeln und in array speichern
imgs_luminance = [cv.cvtColor(img,cv.COLOR_RGB2GRAY) for img in images]

# optional glätten gegen rauschen z.B. mit Gaussian Blur, das erhält aber die Kanten nicht evtl TODO besserer filter hierfür?
    #imgs_smoothed = [cv.GaussianBlur(img, (5,5), 0 ) for img in imgs_luminance]

# gradientenkarten aus den bilddaten berechnen (sobel z.b.)
# bin nicht sicher, wie ich das mache, so dass ich nicht zwei karten habe (x und y gradienten)
# geht aber eventuell auch im vergleich mit zwei karten ?


def estimateReflection(images, light_directions): #eigentlich gradientenkarten statt images zum vergleichen notwendig

    height, width = images[0].shape # Form der Images abgreifen
    initial_reflectance = np.ones((height, width)) # Vollständig weißes Bild als Startwert der Berechnung
    
    def initial_loss_func(reflectance): # parameter für die least_squares, gibt den ersten fehlerwert zurück
        reflectance = reflectance.reshape((height, width))  # Form vom Reflektanzarray anpassen
        residuals = []
        for img, light_dir in zip(images, light_directions):
            # Erwarteten Gradienten aus der aktuellen Reflektanzschätzung berechnen
            expected_gradient = np.dot(reflectance, light_dir)
            # Fehler zwischen dem erwarteten und dem beobachteten Gradienten berechnen
            error = expected_gradient - img
            residuals.extend(error)  # Fehlerliste erweitern
        return residuals

    # Reflektanz schätzen
    result = least_squares(initial_loss_func(initial_reflectance), initial_reflectance.flatten(), method='lm')

# reflektanzschätzung mit least_squares aus scipy.optimize. (numpy.linalg.lstsq wohl besser für lineare probleme(??))
# funktioniert wohl gut für große datensätze und hier lässt sich der algorithmus wählen
# levenberg-marquardt soll ein guter kompromiss aus geschwindigkeit und genauigkeit sein
# mögliche algorithmen: 
#        'trf' : Trust Region Reflective algorithm, particularly suitable for large sparse problems with bounds. Generally robust method.

#        'dogbox' : dogleg algorithm with rectangular trust regions, typical use case is small problems with bounds. Not recommended for problems with rank-deficient Jacobian.

#        'lm' : Levenberg-Marquardt algorithm as implemented in MINPACK. Doesn't handle bounds and sparse Jacobians. Usually the most efficient method for small unconstrained problems.

    # Reflektanz in 2D-Array-Form zurückgeben
    return result.x.reshape((height, width)) 

#normalenberechnung

#normalisieren und visualisieren der normalen
#normalen von [-1,1] auf Bereich von [0,1] skalieren
#auf [0,225] der rgb kanäle umrechnen 
"""