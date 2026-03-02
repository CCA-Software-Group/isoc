"""
Simple wrapper around ezpadova and ezmist that returns isochrone data as an
astropy QTable with physical units attached to each column.
"""

from typing import Dict, Literal, Tuple, Union

from astropy.table import QTable
from astropy import units as u
import numpy as np
import pandas as pd

import ezpadova

from . import mist
from .file_io import load_isochrone
from .units import (
    _COLUMN_ALIASES,
    PADOVA_COLUMN_UNITS,
    MIST_COLUMN_UNITS,
    _get_unit,
    _get_column_units,
    _is_photometry_column,
)

def _dataframe_to_qtable(
    df: pd.DataFrame, column_units: Dict[str, u.UnitBase]
) -> QTable:
    """Convert a pandas DataFrame of isochrone data into an astropy QTable,
    attaching physical units to every column."""
    qt = QTable()
    for col in df.columns:
        qt[col] = np.array(df[col]) * _get_unit(col, column_units)

    if hasattr(df, "attrs") and "comment" in df.attrs:
        qt.meta["comment"] = df.attrs["comment"]
    return qt


class Photometry:
    """Container for photometric magnitude columns.

    Each band is accessible as a named attribute, e.g.
    ``phot.Gmag``, ``phot.G_BPmag``.  The underlying data is stored
    as an `~astropy.table.QTable` available via the ``data`` property.

    Parameters
    ----------
    isochrone : Isochrone
        The parent Isochrone instance from which magnitude columns are
        extracted.  A back-reference is kept so that any columns added
        here (e.g. via :meth:`get_color`) are reflected in the parent
        table.
    """

    def __init__(self, isochrone: "Isochrone"):
        self._isochrone = isochrone
        column_units = _get_column_units(isochrone.database)
        qtable = isochrone.data
        mag_cols = [
            c for c in qtable.columns
            if _is_photometry_column(c, column_units)
        ]
        self._data = qtable[mag_cols] if mag_cols else QTable()

    def get_color(self, band1: str, band2: str) -> u.Quantity:
        """Compute a color index by subtracting two magnitude columns.

        Parameters
        ----------
        band1, band2 : str
            Names of the two magnitude columns.

        Returns
        -------
        color : `~astropy.units.Quantity`
            The ``band1 − band2`` color array.
        """
        color_name = f"{band1.rstrip('mag')}-{band2.rstrip('mag')}"
        if color_name in self._data.colnames:
            print(f"Color '{color_name}' already exists in photometry data.")
            return self._data[color_name]
        
        for b in (band1, band2):
            if b not in self._data.colnames:
                raise ValueError(
                    f"Band '{b}' not found in photometry columns "
                    f"{self._data.colnames}"
                )

        color = self._data[band1] - self._data[band2]
        self._data[color_name] = color
        # Sync the new color column back to the parent Isochrone table
        self._isochrone._data[color_name] = color
        print(f"{color_name} column added to photometry data.")

        return color

    @property
    def data(self) -> QTable:
        """The photometry columns as an `~astropy.table.QTable`."""
        return self._data

    @property
    def columns(self) -> list:
        """List of photometric band names."""
        return self._data.columns

    def __getattr__(self, name: str):
        if name.startswith("_"):
            raise AttributeError(name)
        if "_data" in self.__dict__ and name in self._data.colnames:
            return self._data[name]
        raise AttributeError(
            f"'{type(self).__name__}' object has no attribute '{name}'"
        )

    def __repr__(self) -> str:
        bands = ", ".join(self._data.colnames)
        return f"<Photometry: {bands}>"

    def __len__(self) -> int:
        return len(self._data)


class Isochrone:
    """Unified wrapper that stores isochrone data from either the
    PARSEC/Padova or MIST/MESA service as an `~astropy.table.QTable`
    with units.

    Parameters
    ----------
    database : str
        Backend that produced the data: ``"padova"`` or ``"mist"``.
    """

    def __init__(self, data: QTable = None, database: Literal["padova", "mist"] = "padova"):
        self._database = database
        self._data = data if data is not None else QTable()
        self._column_units = _get_column_units(database)
        self._photometry = Photometry(self)

    @classmethod
    def from_mist(
        cls,
        age: Union[Tuple[float, float, float], list, float, None] = None,
        metallicity: float = 0.0,
        abundance: float = 0.0,
        v_vcrit: float = 0.4,
        output_type: Literal["theory", "photometry"] = "theory",
        extinction: float = 0.0,
        mist_version: Literal["MIST1", "MIST2"] = "MIST1",
        from_file: Union[str, None] = None,
        **kwargs,
        ) -> "Isochrone":    
        """Query the MIST/MESA service and return an :class:`Isochrone`.

        Parameters
        ----------
        age : float, tuple of (low, high, step), list or None
            Age in years or log10(years). A single float queries one isochrone; otherwise 
            multiple isochrones are queried. If age is None, the default MIST age grid is used.
        metallicity : float
             [Fe/H] metallicity value.
        abundance : float
            [alpha/Fe] abundance ratio.
        v_vcrit : float
            Initial rotation velocity v/v_crit.
        output_type : str
            Whether to return "theory" or "photometry" columns.
        extinction : float
            Extinction A_V to apply to photometry (ignored if output_type="theory").
        mist_version : str
            MIST version to query.
        from_file : str or None
            If provided, load isochrone data from a file instead of querying the MIST service.
        **kwargs
            Additional keyword arguments forwarded to the MIST query.

        Returns
        -------
        Isochrone
            An Isochrone object containing the queried data.
        """    

        result = mist.get_isochrones(
            age=age,
            FeH=metallicity,
            alphaFe=abundance,
            v_vcrit=v_vcrit,
            output_type=output_type,
            extinction_Av=extinction,
            mist_version=mist_version, 
            from_file=from_file,           
            **kwargs,
        )

        column_units = _get_column_units("mist")
        result = _dataframe_to_qtable(result, column_units)
        return cls(data=result, database="mist")
    
    @classmethod
    def from_padova(            
        cls,
        age: Union[Tuple[float, float, float], float, None] = None,
        metallicity: Union[Tuple[float, float, float], None] = None,
        metallicity_type: Literal["Z", "MH"] = "Z",
        from_file: Union[str, None] = None,
        **kwargs,
        ) -> "Isochrone":  
        """Query the Padova/PARSEC service and return an :class:`Isochrone`.

        Parameters
        ----------
        age : tuple of (low, high, step) or float or None
            Age in years or log10(years). If age is None, the default Padova age grid is used.
        metallicity : tuple of (low, high, step) or float or None
            Metallicity value. Interpreted as Z or [M/H] depending on metallicity_type. If None, the default Padova metallicity grid is used.
        metallicity_type : str
            Whether the metallicity parameter is interpreted as "Z" or "MH" ([M/H]).
        from_file : str or None
            If provided, load isochrone data from a file instead of querying the Padova service.
        **kwargs
            Additional keyword arguments forwarded to the Padova query. 

        Returns
        -------
        Isochrone
            An Isochrone object containing the queried data.
        """
        if from_file is not None:                
            print(f"Loading Padova isochrone data from file: {from_file}")
            data = load_isochrone(from_file)
            column_units = _get_column_units("padova")
            result = _dataframe_to_qtable(data, column_units)
            return cls(data=result, database="padova")
        
        if metallicity is None:
            MH = None
            print("No metallicity provided. Using default Padova metallicity.")
            ezc = ezpadova.config.configuration['defaults']
            Z = (ezc['isoc_zlow'], ezc['isoc_zupp'], ezc['isoc_dz'])            
        else:
            if isinstance(metallicity, float):
                metallicity = (metallicity, metallicity, 0.0)
            if metallicity_type == "Z":
                Z = metallicity
                MH = None
            else:
                Z = None
                MH = metallicity

        if age is None:
            logage = None
            print("No age provided. Using default Padova age.")
            ezc = ezpadova.config.configuration['defaults']
            age_yr = (ezc['isoc_agelow'], ezc['isoc_ageupp'], ezc['isoc_dage'])
        # infer linear or log scale: log10(14.4 Gyr) = 10.3                    
        else:
            if isinstance(age, float):
                age = (age, age, 0.0)
            if max(age) <= 10.3:
                age_yr = None
                logage = age
                print("Inferred log10 age scale based on age values.")
            else:
                age_yr = age
                logage = None
                print("Inferred linear age scale based on age values.")

        result = ezpadova.get_isochrones(
            age_yr=age_yr,
            Z=Z,
            logage=logage,
            MH=MH,
            return_df=True,
            **kwargs,
        )

        column_units = _get_column_units("padova")
        result = _dataframe_to_qtable(result, column_units)
        return cls(data=result, database="padova")
    
    @classmethod
    def query_ezpadova(
        cls,
        age_yr: Union[Tuple[float, float, float], None] = None,
        Z: Union[Tuple[float, float, float], None] = None,
        logage: Union[Tuple[float, float, float], None] = None,
        MH: Union[Tuple[float, float, float], None] = None,
        default_ranges: bool = False,
        **kwargs,
    ) -> "Isochrone":
        """Query the Padova/PARSEC service and return an :class:`Isochrone`."""

        result = ezpadova.get_isochrones(
            age_yr=age_yr,
            Z=Z,
            logage=logage,
            MH=MH,
            default_ranges=default_ranges,
            return_df=True,
            **kwargs,
        )

        column_units = _get_column_units("padova")
        result = _dataframe_to_qtable(result, column_units)
        return cls(data=result, database="padova")


    def to_isochrones_grid(self, bands: list = None):
        """Export data as a dict of arrays compatible with the
        `isochrones <https://github.com/timothydmorton/isochrones>`_
        ``ModelGrid`` interface.

        Parameters
        ----------
        bands : list of str, optional
            Photometric band columns to include. If *None*, all
            photometry columns are exported.

        Returns
        -------
        dict
            Keys include ``'age'``, ``'feh'``, ``'eep'`` (if available),
            ``'mass'``, ``'logTeff'``, ``'logg'``, ``'logL'``, and one
            entry per band.
        """
        grid = {
            "age": np.array(self.log_age),
            "feh": np.array(self.metallicity),
            "mass": np.array(self.mass),
            "logTeff": np.array(self.log_Teff),
            "logg": np.array(self.log_g),
            "logL": np.array(self.log_L),
        }
        if bands is None:
            bands = self.photometry.columns
        for b in bands:
            grid[b] = np.array(self.photometry.data[b])
        return grid

    @property
    def database(self) -> str:
        """The backend that produced this data (``"padova"`` or ``"mist"``)."""
        return self._database
    
    @property
    def data(self) -> QTable:
        """The full isochrone data as an `~astropy.table.QTable`."""
        return self._data

    @property
    def photometry(self) -> Photometry:
        """Photometric magnitude columns as a :class:`Photometry` object.

        Each band is accessible as a named attribute, e.g.
        ``p.photometry.Gmag``.
        """
        return self._photometry

    @property
    def columns(self) -> list:
        """List of column names."""
        return self._data.columns

    @property
    def n_isochrones(self) -> int:
        """Number of isochrones in the data."""
        return len(np.unique(self.log_age))

    @property
    def metallicity_type(self):
        """Whether the metallicity column is interpreted as "Z" or "MH" ([M/H])."""
        if self._database == "padova":
            return "Z" if "Z" in self._data.colnames else "MH"
        else:
            return "FeH"

    @property
    def log_Teff(self):
        """log₁₀(Teff / K) column."""
        return self._resolve_alias("log_Teff")

    @property
    def log_L(self):
        """log10(L / L_Sun) column."""
        return self._resolve_alias("log_L")

    @property
    def log_g(self):
        """log10(g / (cm s^-2)) column."""
        return self._resolve_alias("log_g")

    @property
    def mass(self):
        """Stellar mass column (M☉)."""
        return self._resolve_alias("mass")

    @property
    def log_age(self):
        """log10(age / yr) column."""
        return self._resolve_alias("log_age")

    @property
    def metallicity(self):
        """Metallicity column ([M/H] for Padova, [Fe/H] for MIST)."""
        return self._resolve_alias("metallicity")

    def _resolve_alias(self, canonical: str):
        """Look up a canonical name in ``_COLUMN_ALIASES`` and return the
        corresponding column from the QTable."""
        actual = _COLUMN_ALIASES[self._database][canonical]
        return self._data[actual]
    
    def __getattr__(self, name: str):
        if name.startswith("_"):
            raise AttributeError(name)
        if "_data" in self.__dict__ and name in self._data.colnames:
            return self._data[name]
        raise AttributeError(
            f"'{type(self).__name__}' object has no attribute '{name}'"
        )

    def __repr__(self) -> str:
        nrows = len(self._data)
        ncols = len(self._data.colnames)
        return f"Isochrone(database={self._database}): {nrows} rows x {ncols} columns"

    def __len__(self) -> int:
        return len(self._data)
