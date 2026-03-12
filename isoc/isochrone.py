"""
Query and process Padova/PARSEC or MIST/MESA isochrone databases to get isochrones
and associated photometry as astropy QTable objects with physical units.
"""

import json
from pathlib import Path
from typing import Literal

import ezpadova
import numpy as np
import pandas as pd
from astropy import units as u
from astropy.table import QTable
from pydantic import validate_call

from . import mist
from .file_io import load_isochrone
from .mist_config import configuration as _mist_cfg
from .padova import _get_padova_photometry_columns, _get_parsec_json
from .units import _get_column_units
from .utilities import _COLUMN_ALIASES, _clean_header_text, _dataframe_to_qtable, _DisplayStr


class _PhotometryTables(dict):
    """Dict subclass returned by `Photometry.data` that also exposes ``.columns``.

    Supports both system access (``data["Roman"]``) and column access
    (``data["Ymag"]``), matching the ``Isochrone.data["col"]`` pattern.
    """

    def __init__(self, tables: dict, photometry: "Photometry"):
        super().__init__(tables)
        self._photometry = photometry

    def __getitem__(self, key: str):
        if key in self.keys():
            return super().__getitem__(key)
        tbl, col = self._photometry._resolve_column(key)
        return tbl[col]

    @property
    def columns(self) -> dict[str, list]:
        """Column names per system — ``{system_full_name: [col1, col2, ...], ...}``."""
        return {name: list(tbl.colnames) for name, tbl in self.items()}


class Photometry:
    """Container for photometric magnitude columns.

    Photometry data is stored in `~astropy.table.QTable` instances,
    one for each photometric system queried.

    Each band is accessible as a named attribute.

    Parameters
    ----------
    isochrone : Isochrone
        The parent Isochrone instance, used to access metadata.
    """

    def __init__(self, isochrone: "Isochrone"):
        self._isochrone = isochrone
        self._tables: dict[str, QTable] = {}  
        self._systems: dict[str, str] = {}    

    @property
    def data(self) -> "_PhotometryTables":
        """Per-system photometry tables.

        Returns
        -------
        _PhotometryTables
            ``{system_full_name: QTable, ...}`` — also exposes ``.columns``.
        """
        return _PhotometryTables(self._tables, self)

    @property
    def systems(self) -> dict[str, str]:
        """Photometric systems currently loaded.

        Returns
        -------
        dict
            ``{short_key: full_name, ...}``
        """
        return dict(self._systems)

    @property
    def available_systems(self) -> dict:
        """All photometric systems available for querying.

        For Padova, systems are parsed from ``ezpadova``'s ``parsec.json``
        (the ``photsys_file`` dictionary).  For MIST, systems are parsed
        from ``isoc``'s ``mist_config.json`` (the ``output`` dictionary).

        Returns
        -------
        dict
            ``{system_value: description, ...}``
        """
        db = self._isochrone.database

        if (db == "mist"):
            pairs = _mist_cfg.get("output", {}).get("output", [])
            return {value: description for description, value in pairs}

        else:
            cfg = _get_parsec_json()
            photsys = cfg.get("photsys_file", {})
            result = {}
            for key, val in photsys.items():
                if isinstance(val, dict):
                    for sub_key, sub_val in val.items():
                        if isinstance(sub_val, list) and len(sub_val) >= 1:
                            desc = sub_val[0] if isinstance(sub_val[0], str) else str(sub_val[0])
                            result[sub_key] = desc
                        elif isinstance(sub_val, str):
                            result[sub_key] = sub_val
                elif isinstance(val, list) and len(val) >= 1:
                    desc = val[0] if isinstance(val[0], str) else str(val[0])
                    result[key] = desc
            return result

    def _system_full_name(self, short_key: str) -> str:
        """Return the full system name for *short_key*, with spaces replaced by underscores."""
        systems = self.available_systems
        desc = systems.get(short_key, short_key)
        return desc.replace(" ", "_")

    @validate_call
    def get_color(self, band1: str, band2: str) -> u.Quantity:
        """Compute a color index by subtracting two magnitude columns.

        The resulting color column is added to the table that contains
        *band1*.

        Parameters
        ----------
        band1, band2 : str
            Names of the two magnitude columns.

        Returns
        -------
        color : `~astropy.units.Quantity`
            The ``band1 − band2`` color array.
        """
        tbl1, col1 = self._resolve_column(band1)
        tbl2, col2 = self._resolve_column(band2)
        color_name = f"{band1}-{band2}"

        if color_name in tbl1.colnames:
            print(f"Color '{color_name}' already exists in photometry data.")
            return tbl1[color_name]

        color = tbl1[col1] - tbl2[col2]
        tbl1[color_name] = color
        print(f"{color_name} column added to photometry table.")

        return color

    @property
    def columns(self) -> dict[str, list]:
        """Column names per system.

        Returns
        -------
        dict
            ``{system_full_name: [col1, col2, ...], ...}``
        """
        return self.data.columns

    def _resolve_column(self, name: str) -> tuple:
        """Resolve a band name to ``(QTable, column_name)``.

        Searches all loaded system tables.  If the name is ambiguous
        across systems, raises a ``ValueError``.

        Returns
        -------
        tuple of (QTable, str)
        """
        matches = []
        for _, tbl in self._tables.items():
            if name in tbl.colnames:
                matches.append((tbl, name))

        if len(matches) == 1:
            return matches[0]
        if len(matches) > 1:
            systems = [sn for sn, tbl in self._tables.items() if name in tbl.colnames]
            raise ValueError(
                f"Ambiguous band name '{name}' found in multiple systems: "
                f"{systems}. Access it via iso.photometry.data['{systems[0]}']['{name}']."
            )

        raise KeyError(
            f"Band '{name}' not found in any photometry table. "
            f"Available columns: {self.columns}"
        )

    # def __getattr__(self, name: str):
    #     if name.startswith("_"):
    #         raise AttributeError(name)
    #     if "_tables" in self.__dict__:
    #         try:
    #             tbl, col = self._resolve_column(name)
    #             return tbl[col]
    #         except (KeyError, ValueError):
    #             pass
    #     raise AttributeError(
    #         f"'{type(self).__name__}' object has no attribute '{name}'"
    #     )

    def __getitem__(self, key: str):
        """Access a photometry system by name or a band column by name.

        If *key* matches a loaded system name, the corresponding
        ``~astropy.table.QTable`` is returned, allowing chained access
        (e.g. ``iso.photometry["Euclid_VIS+NISP_(ABmags)"]["Ymag"]``).

        Otherwise *key* is treated as a band column name and resolved
        across all systems.  A ``ValueError`` is raised if the name is
        ambiguous (present in more than one system).
        """
        if key in self._tables:
            return self._tables[key]
        tbl, col = self._resolve_column(key)
        return tbl[col]

    def __repr__(self) -> str:
        n_systems = len(self._tables)
        info = []
        for name, tbl in self._tables.items():
            info.append(f"{name} ({len(tbl.colnames)} bands)")
        return f"<Photometry: {n_systems} system(s): {', '.join(info)}>"

    def add_photometry(self, system_names: str | list[str]) -> None:
        """Query one or more additional photometric systems and add them.

        Re-uses the query parameters from the parent :class:`Isochrone`,
        changing only the photometric system.

        Parameters
        ----------
        system_names : str or list[str]
            One or more photometric system identifiers (short key or
            long description).
        """
        iso = self._isochrone
        db = iso.database
        qp = iso.query_parameters

        if not qp:
            raise ValueError(
                "Cannot add photometric systems: the parent Isochrone "
                "has no stored query parameters (e.g. loaded from file)."
            )

        if isinstance(system_names, str):
            system_names = [system_names]

        for name in system_names:
            resolved = Isochrone._resolve_photometry_system(name, db)
            if resolved is None:
                raise ValueError(f"Cannot resolve photometric system: {name!r}")

            full_name = self._system_full_name(resolved)

            if (full_name in self._tables):
                print(f"System '{full_name}' is already loaded, skipping.")
                continue

            print(f"Querying {db} for photometric system '{resolved}'...")

            if db == "mist":
                phot_df = mist.get_isochrones(
                    age=qp.get("age"),
                    FeH=qp.get("FeH"),
                    alphaFe=qp.get("alphaFe"),
                    v_div_vcrit=qp.get("v_div_vcrit"),
                    output=resolved,
                    extinction_Av=qp.get("extinction_Av"),
                    version=qp.get("version"),
                    photometry_only=True,
                )

                if isinstance(phot_df, pd.DataFrame) and phot_df.empty:
                    print(f"WARNING: No photometry columns returned for '{resolved}'.")
                    continue

                column_units = _get_column_units("mist")
                phot_qt = _dataframe_to_qtable(phot_df, column_units, database="mist")

            else:
                new_result = ezpadova.get_isochrones(
                    age_yr=qp.get("age_yr"),
                    Z=qp.get("Z"),
                    logage=qp.get("logage"),
                    MH=qp.get("MH"),
                    photsys_file=resolved,
                    return_df=False,
                )

                if not new_result or not new_result.strip() or len(new_result) == 0:
                    raise ValueError("Query returned an empty file - there may be an "
                    "issue with the Padova/PARSEC server.")
                new_result = ezpadova.parsec.parse_result(new_result)

                new_phot_names = _get_padova_photometry_columns(new_result.columns.tolist())
                if not new_phot_names:
                    print(f"WARNING: No photometry columns returned for '{resolved}'.")
                    continue

                column_units = _get_column_units("padova")
                phot_qt = _dataframe_to_qtable(
                    new_result[new_phot_names], column_units, database="padova"
                )

            # validate row count against the first existing table
            for existing_tbl in self._tables.values():
                if len(phot_qt) != len(existing_tbl):
                    raise ValueError(
                        f"Row count mismatch: existing photometry has "
                        f"{len(existing_tbl)} rows but '{resolved}' returned "
                        f"{len(phot_qt)} rows."
                    )
                break

            self._tables[full_name] = phot_qt
            self._systems[resolved] = full_name

            # store per-system comment
            comment = phot_qt.meta.get("comment", "")
            phot_qt.meta[f"comment_{resolved}"] = comment

            print(f"Added system '{full_name}' with {len(phot_qt.colnames)} columns: "
                  f"{phot_qt.colnames}")

    @property
    def header(self) -> str:
        """Header metadata for each photometric system."""
        sections = []

        for short_key, full_name in self._systems.items():
            title = f"PHOTOMETRY.{short_key}"
            tbl = self._tables.get(full_name)
            if tbl is None:
                sections.append(title)
                continue

            raw = tbl.meta.get(f"comment_{short_key}", "")
            if not raw:
                raw = tbl.meta.get("comment", "")

            if raw:
                sections.append(f"{title}\n{raw}")
            else:
                sections.append(title)

        if not sections:
            return _DisplayStr("No photometry header available.")

        return _DisplayStr("\n\n".join(sections))


class _IsochroneIndex:
    """Indexer returned by ``Isochrone.isochrone``.

    Supports integer indexing (``iso.isochrone[0]``) and
    ``'field=value'`` string indexing (``iso.isochrone['log_age=9']``).
    Each item returned is a new :class:`Isochrone` containing only the
    rows that belong to that individual isochrone.
    """

    def __init__(self, isochrone: "Isochrone"):
        self._iso = isochrone

    @staticmethod
    def _to_float_array(col) -> np.ndarray:
        """Strip astropy units and return a float64 numpy array."""
        arr = col
        if hasattr(arr, "value"):
            arr = arr.value
        return np.asarray(arr, dtype=float)

    def _unique_groups(self) -> list[tuple]:
        """Return ordered list of ``(mask, label)`` for each unique isochrone.

        Groups are formed by the unique combinations of log_age and
        initial metallicity.  The ``metallicity`` alias is not
        used because it resolves to the evolving [Fe/H];
        instead initial-metallicity columns are used
        (``[Fe/H]_init`` for MIST, ``Z`` / ``MH`` for Padova), which are
        constant for all stars on a single isochrone.
        """
        iso = self._iso
        data = iso._data

        key_cols: dict[str, np.ndarray] = {}

        # age (always the primary grouping column)
        try:
            key_cols["log_age"] = self._to_float_array(iso._resolve_alias("log_age"))
        except KeyError:
            pass

        # initial metallicity — constant per isochrone, unlike
        # [Fe/H] (MIST) or Z (Padova) columns.  Preference order:
        #   MIST: [Fe/H]_init > [a/Fe]_init
        #   Padova: Zini > MH
        for cand in ("[Fe/H]_init", "Zini", "MH", "[a/Fe]_init"):
            if cand in data.colnames:
                vals = self._to_float_array(data[cand])
                if len(np.unique(np.round(vals, 8))) > 1:
                    key_cols[cand] = vals
                break

        if not key_cols:
            return [(np.ones(len(data), dtype=bool), "0")]

        names = list(key_cols.keys())
        arrays = list(key_cols.values())

        # collect unique combinations in original row order
        seen: set = set()
        unique_combos: list = []
        for row in zip(*arrays):
            k = tuple(round(x, 8) for x in row)
            if k not in seen:
                seen.add(k)
                unique_combos.append(tuple(row))

        groups = []
        for combo in unique_combos:
            mask = np.ones(len(data), dtype=bool)
            for arr, val in zip(arrays, combo):
                mask &= np.isclose(arr, val)
            label = ",".join(f"{n}={v:.6g}" for n, v in zip(names, combo))
            groups.append((mask, label))
        return groups

    def __len__(self) -> int:
        return len(self._unique_groups())

    def __iter__(self):
        for mask, _ in self._unique_groups():
            yield self._iso._subset(mask)

    @property
    def labels(self) -> list[str]:
        """Labels for each isochrone, e.g. ``['log_age=9', 'log_age=9.5']``."""
        return [label for _, label in self._unique_groups()]

    def __getitem__(self, key):
        groups = self._unique_groups()

        if isinstance(key, int):
            n = len(groups)
            if key < -n or key >= n:
                raise IndexError(
                    f"isochrone index {key} out of range for {n} isochrone(s)"
                )
            mask, _ = groups[key % n]

        elif isinstance(key, str):
            # try exact label match first
            for mask, label in groups:
                if label == key:
                    break
            else:
                mask = self._parse_field_key(key)

        else:
            raise TypeError(
                f"isochrone index must be int or str, got {type(key).__name__!r}"
            )

        return self._iso._subset(mask)

    def _parse_field_key(self, key: str) -> np.ndarray:
        """Parse ``'field=value'`` and return a boolean row mask."""
        if "=" not in key:
            raise KeyError(
                f"Cannot parse isochrone key {key!r}. "
                "Expected integer index or 'field=value' string."
            )
        field, _, val_str = key.partition("=")
        field = field.strip()
        val = float(val_str.strip())

        iso = self._iso
        try:
            col_values = self._to_float_array(iso._resolve_alias(field))
        except KeyError:
            if field in iso._data.colnames:
                col_values = self._to_float_array(iso._data[field])
            else:
                raise KeyError(
                    f"Unknown field {field!r}. "
                    f"Use a column name from: {iso._data.colnames}."
                )

        mask = np.isclose(col_values, val)
        if not np.any(mask):
            raise KeyError(
                f"No rows found with {field}={val}. "
                f"Available values: {np.unique(col_values)}"
            )
        return mask

    def __repr__(self) -> str:
        groups = self._unique_groups()
        labels = [label for _, label in groups]
        return f"<IsochroneIndex: {len(groups)} isochrone(s): {labels}>"


class Isochrone:
    """Wrapper that stores isochrone data from either the
    PARSEC/Padova or MIST/MESA service as an `~astropy.table.QTable`
    with units.

    Parameters
    ----------
    database : str
        Backend that produced the data: ``"padova"`` or ``"mist"``.
    """

    def __init__(self, database: Literal["padova", "mist"], data: QTable = None):
        self._database = database
        self._data = data if data is not None else QTable()
        self._column_units = _get_column_units(database)
        self._photometry = Photometry(self)
        self._query_parameters = {}

    @staticmethod
    def default_values(database: Literal["padova", "mist"]) -> dict:
        """Get the default query parameters.

        Returns
        -------
        dict
            A copy of the default query parameters.
            The `aliases` key maps the parameter name expected by the web server to the
            generalized arg names in :meth:`from_padova` or :meth:`from_mist`.
        """
        if database == "mist":
            defaults = _mist_cfg['defaults'].copy()
            defaults['_aliases'] = {
                'FeH_value': 'metallicity',
                'afe': 'abundance',
                'output': 'photometry',
                'Av_value': 'extinction',
            }
        else:
            ezc = ezpadova.config.configuration
            defaults = ezc.get('defaults', {})

            defaults['_aliases'] = {
                'age_yr': 'age',
                'logage': 'age',
                'Z': 'metallicity_type',
                'MH': 'metallicity_type',
            }

        return defaults

    @staticmethod
    def parameter_descriptions(database: Literal["padova", "mist"]) -> dict:
        """Get descriptions for each query parameter."""
        if database == "mist":
            print("See https://mist.science/interp_isos.html and https://www.mist.science/resources.html")
        else:
            print("See https://stev.oapd.inaf.it/cgi-bin/cmd, https://github.com/mfouesneau/ezpadova/blob/master/src/ezpadova/parsec.md and https://stev.oapd.inaf.it/cmd_3.9/help.html")


    @classmethod
    def from_mist(
        cls,
        age: tuple[float, float, float] | list | float | None = None,
        metallicity: float | None = None,
        abundance: float | None = None,
        v_div_vcrit: float | None = None,
        photometry: str | None = None,
        extinction: float | None = None,
        version: Literal["MIST1", "MIST2", None] = None,
        from_file: str | None = None,
        **kwargs,
        ) -> "Isochrone":
        """Query the MIST/MESA service and return an :class:`Isochrone`.

        Any parameters passed as ``None`` will use the MIST defaults 
        (see `Isochrone.default_values`).

        Parameters
        ----------
        age : float, tuple of (low, high, step), list or None
            Age in years or log10(years). A single float queries one isochrone; a tuple of 
            length 3 sets a min, max and step size to query over the corresponding age grid, 
            and a list queries over an age grid.
        metallicity : float or None
             [Fe/H] metallicity value.
        abundance : float or None
            [alpha/Fe] abundance ratio.
        v_div_vcrit : float or None
            Initial rotation velocity v/v_crit.
        photometry : str or None
            The name of a photometric system to retrieve synthetic photometry for.
            If None, MIST output is set to "theory".
        extinction : float or None
            Extinction A_V to apply to photometry.  Has no effect if *photometry* is 
            ``None``.
        version : str or None
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

        # resolve photometry system (short key or long description)
        photometry = cls._resolve_photometry_system(photometry, "mist")

        result = mist.get_isochrones(
            age=age,
            FeH=metallicity,
            alphaFe=abundance,
            v_div_vcrit=v_div_vcrit,
            output=photometry,
            extinction_Av=extinction,
            version=version,
            from_file=from_file,
            **kwargs,
        )

        # get_isochrones returns either a tuple (theory_df, phot_df, phot_cols)
        # when the server sent a multi-file zip, or a single DataFrame.
        if isinstance(result, tuple):
            theory_df, phot_df, phot_cols = result
        else:
            theory_df = result
            phot_df, phot_cols = pd.DataFrame(), []

        column_units = _get_column_units("mist")
        theory_qt = _dataframe_to_qtable(theory_df, column_units, database="mist")
        iso = cls(data=theory_qt, database="mist")

        iso._query_parameters = {
            "age": age,
            "FeH": metallicity,
            "alphaFe": abundance,
            "v_div_vcrit": v_div_vcrit,
            "output_option": "photometry" if photometry is not None else "theory",
            "output": photometry if photometry is not None else None,
            "extinction_Av": extinction,
            "version": version,
            **kwargs,
        }

        # put photometry in own table
        if phot_cols and not phot_df.empty:
            phot_qt = _dataframe_to_qtable(phot_df, column_units, database="mist")

            # record which system these columns belong to
            system_key = (iso._query_parameters.get("output")
                          or phot_df.attrs.get("photometry_system")
                          or "unknown")
            full_name = iso._photometry._system_full_name(system_key)

            iso._photometry._tables[full_name] = phot_qt
            iso._photometry._systems[system_key] = full_name

            # store per-system comment in photometry meta
            comment = phot_qt.meta.get("comment", theory_qt.meta.get("comment", ""))
            phot_qt.meta[f"comment_{system_key}"] = _clean_header_text(comment, "mist")

        return iso

    @classmethod
    def from_padova(
        cls,
        age: tuple[float, float, float] | float | None = None,
        metallicity: tuple[float, float, float] | float | None = None,
        metallicity_type: Literal["Z", "MH", None] = None,
        photometry: str | None = None,
        from_file: str | None = None,
        **kwargs,
        ) -> "Isochrone":
        """Query the Padova/PARSEC service and return an :class:`Isochrone`.

        Any parameters passed as None will use the Padova/PARSEC defaults 
        (see `Isochrone.default_values`).

        Parameters
        ----------
        age : tuple of (low, high, step) or float or None
            Age in years or log10(years). A single float queries one isochrone; a tuple of 
            length 3 sets a min, max and step size to query over the corresponding age grid, 
            and a list queries over an age grid.
        metallicity : tuple of (low, high, step) or float or None
            Metallicity value. Interpreted as Z or [M/H] depending on metallicity_type.
        metallicity_type : str or None
            Whether the metallicity parameter is interpreted as "Z" or "MH" ([M/H]).
        photometry : str or None
            The name of a photometric system to retrieve synthetic photometry for.
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
            print(f"'from_file' is not None. Loading isochrone data from file: {from_file} " \
                  "rather than performing a query.")
            data = load_isochrone(from_file)
            if isinstance(data, str):
                data = data.encode("utf-8")
            result = ezpadova.parsec.parse_result(data)
            return cls._padova_post_processing(result=result, query_parameters={})

        if metallicity is None and metallicity_type is None:
            MH = None
            ezc = ezpadova.config.configuration['defaults']
            Z = (ezc['isoc_zlow'], ezc['isoc_zupp'], ezc['isoc_dz'])
            print("Both 'metallicity' and 'metallicity_type' are None. " \
            f"Using default Padova metallicity grid, Z: {Z}.")
        elif (metallicity is not None and metallicity_type is None) or (metallicity is None and metallicity_type is not None):
            raise ValueError("If 'metallicity' is specified, 'metallicity_type' must " \
            "also be specified, and vice versa.")
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
            ezc = ezpadova.config.configuration['defaults']
            age_yr = (ezc['isoc_agelow'], ezc['isoc_ageupp'], ezc['isoc_dage'])
            print(f"'age' is None. Using default Padova age grid: {age_yr}.")
        # infer linear or log scale: log10(14.4 Gyr) = 10.3
        else:
            if isinstance(age, float):
                max_age = age
                age = (age, age, 0.0)
            if isinstance(age, tuple):
                max_age = max(age[:2])
            if max_age <= 10.3:
                age_yr = None
                logage = age
                print(f"Inferring log10 age scale based on age values {age}.")
            else:
                age_yr = age
                logage = None
                print(f"Inferring linear age scale based on age values {age}.")

        kw = dict(
            age_yr=age_yr,
            Z=Z,
            logage=logage,
            MH=MH,
            return_df=False,
            **kwargs,
        )

        if photometry is None:
            print("'photometry' is None. Using default ezpadova photometric system.") 
        else:
            # resolve photometry system (short key or long description)
            photometry = cls._resolve_photometry_system(photometry, "padova")
            kw["photsys_file"] = photometry
        
        print("\n")
        result = ezpadova.get_isochrones(**kw)

        if not result or not result.strip() or len(result) == 0:
            raise ValueError("Query returned an empty file - there may be an " \
            "issue with the Padova/PARSEC server.")
        result = ezpadova.parsec.parse_result(result)

        query_parameters = {
            'age_yr': age_yr,
            'logage': logage,
            'Z': Z,
            'MH': MH,
            'photsys_file': photometry,
            **kwargs,
        }
        print(f"User-supplied query parameters (as seen by ezpadova):\n\t{query_parameters}")

        iso = cls._padova_post_processing(result=result, query_parameters=query_parameters)
        print(f"All query parameters (including defaults for those not specified):\n\t{iso.query_parameters}")
        return iso

    @classmethod
    def query_ezpadova(
        cls,
        age_yr: tuple[float, float, float] | None = None,
        Z: tuple[float, float, float] | None = None,
        logage: tuple[float, float, float] | None = None,
        MH: tuple[float, float, float] | None = None,
        default_ranges: bool = False,
        **kwargs,
    ) -> "Isochrone":
        """Query the Padova/PARSEC service and return an :class:`Isochrone`."""

        # resolve photometry system (short key or long description)
        if 'photsys_file' in kwargs and kwargs['photsys_file'] is not None:
            kwargs['photsys_file'] = cls._resolve_photometry_system(kwargs['photsys_file'], "padova")

        result = ezpadova.get_isochrones(
            age_yr=age_yr,
            Z=Z,
            logage=logage,
            MH=MH,
            default_ranges=default_ranges,
            return_df=False,
            **kwargs,
        )

        if not result or not result.strip() or len(result) == 0:
            raise ValueError("Query returned an empty file - there may be an " \
            "issue with the Padova/PARSEC server.")
        result = ezpadova.parsec.parse_result(result)

        query_parameters = {
            'age_yr': age_yr,
            'logage': logage,
            'Z': Z,
            'MH': MH,
            'photsys_file': kwargs.get('photsys_file'),
            **kwargs,
        }
        print(f"User-supplied query parameters (as seen by ezpadova):\n\t{query_parameters}")

        iso = cls._padova_post_processing(result=result, query_parameters=query_parameters)
        print(f"All query parameters (including defaults for those not specified by user):\n\t{iso.query_parameters}")
        return iso

    @classmethod
    def _padova_post_processing(cls, result: pd.DataFrame, query_parameters: dict) -> "Isochrone":
        """Post-processing for Padova queries.

        Parameters
        ----------
        result : pd.DataFrame
            The DataFrame returned by ``ezpadova.get_isochrones``.
        query_parameters : dict
            The resolved query parameters.

        Returns
        -------
        Isochrone
        """
        ezc = ezpadova.config.configuration['defaults']
        for key, val in ezc.items():
            if key not in query_parameters:
                query_parameters[key] = val

        column_units = _get_column_units("padova")
        qt = _dataframe_to_qtable(result, column_units, database="padova")
        iso = cls(data=qt, database="padova")
        iso._query_parameters = query_parameters
        iso._split_padova_photometry()

        return iso

    def _split_padova_photometry(self):
        """Move photometry columns from ``_data`` into ``_photometry``."""
        phot_names = _get_padova_photometry_columns(self._data.colnames)
        phot_table = QTable()

        for col in phot_names:
            phot_table[col] = self._data[col]
            self._data.remove_column(col)

        # record which system these columns belong to
        system_key = self._query_parameters.get("photsys_file") or "unknown"
        full_name = self._photometry._system_full_name(system_key)

        self._photometry._tables[full_name] = phot_table
        self._photometry._systems[system_key] = full_name

        # store per-system comment in photometry meta
        comment = _clean_header_text(self._data.meta.get("comment", ""), self._database)
        phot_table.meta[f"comment_{system_key}"] = comment

    def get_photometry_system_title(self) -> str | None:
        """Look up the human-readable title for the queried photometric system."""
        if self._database == "mist":
            system_key = self._query_parameters.get("output", None)
        else:
            system_key = self._query_parameters.get("photsys_file", None)
        if system_key is None:
            return None

        systems = self._photometry.available_systems
        return systems.get(system_key, None)

    @classmethod
    def _resolve_photometry_system(cls, name: str | None, database: Literal["padova", "mist"]) -> str | None:
        """Resolve a photometric system name to the short key expected by the server.

        *name* may be the short key (e.g. ``"UBVRIplus"`` or ``"ubvrijhk"``)
        or the long human-readable description (e.g.
        ``"UBVRIJHK (cf. Maiz-Apellaniz 2006 + Bessell 1990)"``).
        Returns the short key, or *None* if *name* is *None*.

        Parameters
        ----------
        name : str or None
            Photometric system identifier (short or long form).
        database : ``"padova"`` or ``"mist"``
            Which backend's system list to search.

        Returns
        -------
        str or None
            The short key recognised by the server.

        Raises
        ------
        ValueError
            If *name* is not recognised.
        """
        if name is None:
            return None

        # build a temporary Photometry to access available_systems
        # without requiring a full Isochrone instance.
        tmp = cls(database=database)
        systems = tmp.photometry.available_systems

        # direct match on short key (case-sensitive)
        if name in systems:
            return name

        # match on description (case-insensitive)
        name_lower = name.lower()
        for key, desc in systems.items():
            if not isinstance(desc, str):
                continue
            if desc.lower() == name_lower:
                return key

        raise ValueError(
            f"Photometric system '{name}' not recognised for database "
            f"'{database}'. Use Isochrone.photometry.available_systems "
            f"to see available systems."
        )

    @property
    def database(self) -> str:
        """Backend that produced this data (``"padova"`` or ``"mist"``)."""
        return self._database

    @property
    def data(self) -> QTable:
        """Isochrone data (excluding photometry) as an `~astropy.table.QTable`."""
        return self._data

    @property
    def photometry(self) -> Photometry:
        """Photometric magnitude columns as a :class:`Photometry` object."""
        return self._photometry

    @property
    def columns(self) -> list:
        """List of column names."""
        return self._data.columns

    @property
    def n_isochrones(self) -> int:
        """Number of isochrones in the data."""
        ages = self._resolve_alias("log_age")
        return len(np.unique(ages))

    @property
    def isochrone(self) -> "_IsochroneIndex":
        """Index individual isochrones within a multi-isochrone table.

        Supports integer and ``'field=value'`` string keys.  Each item
        is a new :class:`Isochrone` containing only the rows for that
        individual isochrone.

        Examples
        --------
        >>> iso.isochrone[-1]                    
        >>> iso.isochrone['log_age=9']          # MIST
        >>> iso.isochrone['logAge=9']           # Padova
        >>> iso.isochrone['[Fe/H]_init=0.015']  # MIST: initial metallicity        
        >>> iso.isochrone['Zini=0.015']         # Padova: initial metallicity
        """
        return _IsochroneIndex(self)

    def _subset(self, mask: np.ndarray) -> "Isochrone":
        """Return a new Isochrone containing only the rows selected by *mask*."""
        new_iso = Isochrone.__new__(Isochrone)
        new_iso._data = self._data[mask]
        new_iso._database = self._database
        new_iso._query_parameters = self._query_parameters.copy()
        new_iso._photometry = Photometry(new_iso)
        for full_name, tbl in self._photometry._tables.items():
            new_iso._photometry._tables[full_name] = tbl[mask]
        new_iso._photometry._systems = self._photometry._systems.copy()
        return new_iso

    @property
    def log_Teff(self):
        """log10(Teff [K]) column."""
        return self._resolve_alias("log_Teff")

    @property
    def log_L(self):
        """log10(L [L_Sun]) column."""
        return self._resolve_alias("log_L")

    @property
    def log_g(self):
        """log10(g [cm s^-2]) column."""
        return self._resolve_alias("log_g")

    @property
    def initial_mass(self):
        """Stellar mass column [M_Sun]."""
        return self._resolve_alias("initial_mass")

    @property
    def mass(self):
        """Stellar mass column [M_Sun]."""
        return self._resolve_alias("mass")

    @property
    def log_age(self):
        """log10(age / [yr]) column."""
        return self._resolve_alias("log_age")

    @property
    def initial_metallicity(self):
        """Initial metallicity column."""
        return self._resolve_alias("initial_metallicity")
    
    @property
    def metallicity(self):
        """Metallicity column."""
        return self._resolve_alias("metallicity")

    @property
    def metallicity_type(self):
        """Whether the metallicity column is ``"Z"``, ``"MH"`` ([M/H]), or ``"FeH"`` ([Fe/H])."""
        if self._database == "mist":
            return "FeH"

        qp = self._query_parameters
        if (qp.get("MH") is not None):
            return "MH"
        else:
            return "Z"

    @property
    def query_parameters(self) -> dict:
        """The resolved query parameters used to retrieve this isochrone.

        Returns
        -------
        dict
            A copy of the query parameters sent to the webform.
        """
        return self._query_parameters.copy()

    @property
    def header(self) -> str:
        """Header metadata from the original isochrone file/query."""
        return _DisplayStr(self._data.meta.get("comment", ""))


    def _resolve_alias(self, generic_name: str):
        """Resolve a generic property name to a data column and return it.

        Checks the database-specific column alias table first, then
        falls back to the config-level ``_aliases`` dict.

        Parameters
        ----------
        generic_name : str
            Generic name like ``"metallicity"``, ``"log_Teff"``, etc.

        Returns
        -------
        astropy QTable Column
        """
        col_aliases = _COLUMN_ALIASES.get(self._database, {})
        col_name = col_aliases.get(generic_name)

        # 0. dynamic resolution for metallicity
        if generic_name == "metallicity":
            if self._database == "mist":
                return self._data["[Fe/H]"]
            elif self._database == "padova":
                qp = self._query_parameters
                if qp.get("MH") is not None:
                    return self._data["MH"]
                else:
                    return self._data["Z"]

        if generic_name == "initial_metallicity":
            if self._database == "mist":
                return self._data["[Fe/H]_init"]
            elif self._database == "padova":
                qp = self._query_parameters
                if qp.get("MH") is not None:
                    return self._data["MH"]
                else:
                    return self._data["Zini"]

        # 1. check hard-coded column aliases for this database
        if col_name and col_name in self._data.colnames:
            return self._data[col_name]

        # 2. fall back to config-level aliases (query param names)
        aliases = self._query_parameters.get("_aliases", {})
        actual = aliases.get(generic_name, generic_name)
        if actual in self._data.colnames:
            return self._data[actual]

        # 3. try the generic name directly
        if generic_name in self._data.colnames:
            return self._data[generic_name]

        raise KeyError(
            f"Cannot resolve '{generic_name}' for database "
            f"'{self._database}'. Tried column names: "
            f"{[col_name, actual, generic_name]}. "
            f"Available columns: {self._data.colnames}"
        )


    # def __getattr__(self, name: str):
    #     if name.startswith("_"):
    #         raise AttributeError(name)
    #     if "_data" in self.__dict__ and name in self._data.colnames:
    #         return self._data[name]
    #     raise AttributeError(
    #         f"'{type(self).__name__}' object has no attribute '{name}'"
    #     )

    def __repr__(self) -> str:
        nrows = len(self._data)
        ncols = len(self._data.colnames)
        return f"Isochrone(database={self._database}): {nrows} rows x {ncols} columns"

    def __len__(self) -> int:
        return len(self._data)


# apply validate_call after the class is fully defined so that
# the "Isochrone" forward reference can be resolved.
Isochrone.from_mist = classmethod(validate_call(Isochrone.from_mist.__func__))
Isochrone.from_padova = classmethod(validate_call(Isochrone.from_padova.__func__))
Isochrone.query_ezpadova = classmethod(validate_call(Isochrone.query_ezpadova.__func__))
