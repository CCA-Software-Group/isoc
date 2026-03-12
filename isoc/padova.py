import requests

from .utilities import _COLUMN_ALIASES

_PARSEC_JSON_URL = (
    "https://raw.githubusercontent.com/mfouesneau/ezpadova/"
    "master/src/ezpadova/parsec.json"
)
# session-level cache
_parsec_json_cache: dict = {}


def _get_parsec_json() -> dict:
    """Download and cache ``parsec.json`` from the ezpadova GitHub repo.

    Returns
    -------
    dict
        The parsed JSON configuration.
    """
    if _parsec_json_cache:
        return _parsec_json_cache

    print(f"Downloading parsec.json from {_PARSEC_JSON_URL}")
    resp = requests.get(_PARSEC_JSON_URL, timeout=30)
    resp.raise_for_status()
    cfg = resp.json()
    _parsec_json_cache.update(cfg)
    return _parsec_json_cache


def _get_padova_photometry_columns(column_names: list[str]) -> list[str]:
    """Identify photometry columns in a Padova isochrone table.

    The Padova service does not have a standard way to identify photometry
    columns, so any column ending in "mag" that is not
    a known theory column is treated as photometry.

    Parameters
    ----------
    column_names : list of str
        Column names from a Padova isochrone table.

    Returns
    -------
    list of str
        List of column names corresponding to photometry.
    """
    theory_cols = set(_COLUMN_ALIASES.get("padova", {}).values())
    phot_names = [
        c for c in column_names
        if c.endswith("mag") and c not in theory_cols
    ]
    return phot_names
