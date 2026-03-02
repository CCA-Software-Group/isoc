"""
isoc - Unified package for downloading Mist and Padova isochrones

This package provides a unified object-oriented interface to download stellar
isochrones from Mist/MESA and Padova/PARSEC websites.

All data is stored as astropy Tables for seamless integration with the
astronomy ecosystem.
"""

from .isochrone import Isochrone

__version__ = "0.1.0"
__all__ = ["Isochrone"]
