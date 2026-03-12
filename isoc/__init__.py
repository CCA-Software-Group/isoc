"""
isoc - Download and process MIST/MESA and Padova/PARSEC isochrones
"""

from .isochrone import Isochrone, Photometry
from .plot import plot_color_magnitude, plot_isochrone

__version__ = "0.1.0"
__all__ = ["Isochrone", "Photometry", "plot_isochrone", "plot_color_magnitude"]
