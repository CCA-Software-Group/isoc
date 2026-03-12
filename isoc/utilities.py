import numpy as np
import pandas as pd
from astropy import units as u
from astropy.table import QTable

from .units import _get_unit


def _clean_header_text(raw, database: str = None) -> str:
    """Clean raw header metadata into a readable string.

    For MIST data, strips trailing lines that are purely numeric.
    Removes trailing blank lines.

    Parameters
    ----------
    raw : str or dict
        The raw header text or metadata dict.
    database : str, optional
        ``"mist"`` or ``"padova"``.

    Returns
    -------
    str
    """
    if isinstance(raw, dict):
        raw = "\n".join(f"{k}: {v}" for k, v in raw.items())
    elif not isinstance(raw, str):
        raw = str(raw)

    lines = raw.split("\n")

    if database == "mist":
        while lines and lines[-1].strip():
            tokens = lines[-1].strip().split()
            try:
                [float(t) for t in tokens]
                lines.pop()
            except ValueError:
                break

    while lines and not lines[-1].strip():
        lines.pop()

    return "\n".join(lines)

class _DisplayStr(str):
    """A str subclass whose repr prints with newlines."""
    def __repr__(self) -> str:
        return str(self)

# generalized property names to column names
_COLUMN_ALIASES = {
    "padova": {
        "log_Teff": "logTe",
        "log_L":    "logL",
        "log_g":    "logg",
        "initial_mass": "Mini",
        "mass":     "Mass",
        "log_age":  "logAge",
        # 'metallicity' is resolved dynamically in Isochrone._resolve_alias
    },
    "mist": {
        "log_Teff": "log_Teff",
        "log_L":    "log_L",
        "log_g":    "log_g",
        "initial_mass": "initial_mass",
        "mass":     "star_mass",
        "log_age":  "log10_isochrone_age_yr",
        "metallicity": "[Fe/H]",
    },
}

def _dataframe_to_qtable(
    df: pd.DataFrame, column_units: dict[str, u.UnitBase],
    database: str = None,
) -> QTable:
    """Convert a pandas DataFrame of isochrone data into an astropy QTable,
    attaching physical units to every column."""
    qt = QTable()
    for col in df.columns:
        qt[col] = np.array(df[col]) * _get_unit(col, column_units)

    # preserve pandas attrs (e.g. 'comment') as QTable meta
    if hasattr(df, "attrs") and df.attrs:
        qt.meta.update(df.attrs)
        if "comment" in qt.meta:
            qt.meta["comment"] = _clean_header_text(qt.meta["comment"], database)

    return qt
