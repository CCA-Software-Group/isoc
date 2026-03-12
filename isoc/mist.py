import re
import zlib
from io import BytesIO
from typing import Literal

import pandas as pd
import requests
from bs4 import BeautifulSoup

from .file_io import extract_zip, load_isochrone
from .mist_config import configuration as _cfg

_MIST_THEORY_COLUMNS = {
    "[Fe/H]_init", "[Fe/H]",
    "EEP", "log10_isochrone_age_yr",
    "initial_mass", "star_mass",
    "log_Teff", "log_g", "log_L", "log_R",
    "Av", "phase",
    "[a/Fe]_init", "[a/Fe]",
}

def _build_query(**kw) -> str:
    """Build a URL-encoded query string from the given keyword arguments.

    Only includes keys listed in the configuration's ``query_options``
    list, matching the fields the MIST server expects.  Replaces
    ``None`` values with empty strings.

    Parameters
    ----------
    kw : dict
        Query parameters, already merged with defaults.

    Returns
    -------
    str
        A URL-encoded query string (joined by ``&``).
    """
    keys = _cfg.get("query_options", list(kw.keys()))
    q = []
    for k in keys:
        val = kw.get(k, "")
        if val is None:
            val = ""
        q.append(f"{k}={val}")
    return '&'.join(q)


def _file_type(data: bytes):
    """Detect archive type from the first bytes of *data*.

    Returns ``'gz'``, ``'bz2'``, or ``'zip'`` when a known magic
    sequence is found, otherwise ``None``.
    """
    magic_dict = {
        b"\x1f\x8b\x08": "gz",
        b"\x42\x5a\x68": "bz2",
        b"\x50\x4b\x03\x04": "zip",
    }
    for magic, filetype in magic_dict.items():
        if data[:len(magic)] == magic:
            return filetype
    return None


def query(q: str) -> bytes | dict:
    """Query the MIST webpage with the given parameters.

    Sends a POST request to the MIST webpage specified in the
    configuration and retrieves the resulting data. The data is processed
    and returned as bytes. If the server response is incorrect or if there is
    an issue with the data retrieval, a RuntimeError is raised.

    Args:
        q: URL-encoded query string.

    Returns:
        bytes or dict: The retrieved data from the MIST webpage.
            When the download is a zip archive containing multiple files,
            a ``dict`` mapping filenames to their byte content is returned.
            Otherwise raw bytes of the single file.

    Raises:
        RuntimeError: If the server response is incorrect or if there is an
                      issue with data retrieval.
    """
    url = _cfg["request_url"]
    # use HTTPS to avoid HTTP -> HTTPS redirects that drop POST body
    if url.startswith("http://"):
        url = url.replace("http://", "https://", 1)
    print(f"Querying {url}")
    print(f"Query parameters sent to the MIST server:\n\t{q.replace('&', '\n\t')}")
    c = requests.post(
        url,
        data=q.encode('utf8'),
        headers={'Content-Type': 'application/x-www-form-urlencoded'},
        timeout=600,
    ).text

    # extract download link from server response
    soup = BeautifulSoup(c, "html.parser")
    link = soup.find("a", href=True)
    if link is None:
        error_text = soup.get_text(separator="\n", strip=True)
        raise RuntimeError(
            f"MIST query failed.\n"
            f"Server response: {error_text[:1500]}\n"
            f"Query sent: {q}\n\n"
        )

    fname = link["href"]

    # build download URL from the site root
    base_url = re.match(r'https?://[^/]+', url).group(0)
    if fname.startswith("http"):
        data_url = fname
    elif fname.startswith("/"):
        data_url = base_url + fname
    else:
        data_url = base_url + "/" + fname

    print(f"Downloading data from {data_url}")
    r = requests.get(data_url, timeout=600).content
    typ = _file_type(r)
    if typ is not None:
        if 'zip' in typ:
            return extract_zip(bytes(r))
        else:
            r = zlib.decompress(bytes(r), 15 + 32)
    return r


def parse_result(data: str | bytes | dict, photometry_only: bool = False) -> pd.DataFrame | tuple[pd.DataFrame, pd.DataFrame, list]:
    """Parse MIST isochrone data.

    *data* may be:

    * **dict** – mapping of ``{filename: text_content}`` extracted from
      a zip archive.  When both a ``.iso`` and a ``.iso.<system>`` file
      are present, the photometry file is parsed and the photometry columns
      (those not in the theory-only ``.iso`` header) are identified.
    * **bytes** – raw content returned by the MIST server (possibly
      gzip- or zip-compressed).
    * **str that is a file path** – a local file containing isochrone data.
    * **str of file content** – the decoded text of an isochrone file.

    Parameters
    ----------
    data : dict, str, or bytes
        Raw server content, extracted zip dict, a file path, or decoded text.
    photometry_only : bool, optional
        If *True* and *data* is a zip dict containing both theory and
        photometry files, returns only a ``pd.DataFrame`` of photometry
        columns.  Otherwise returns a 3-tuple
        ``(theory_df, phot_only_df, phot_columns)``.

    Returns
    -------
    pd.DataFrame or tuple
        * When *data* is a zip dict and ``photometry_only=False``:
          ``(theory_df, phot_only_df, phot_columns)`` where
          *theory_df* contains all non-photometry columns, *phot_only_df*
          contains only the photometry columns, and *phot_columns* is the
          list of photometry column names.
        * When *data* is a zip dict and ``photometry_only=True``:
          a single ``pd.DataFrame`` of photometry columns.
        * Otherwise: a single ``pd.DataFrame`` with the file header stored
          in ``df.attrs["comment"]``.
    """
    # handle dict from multi-file zip
    if isinstance(data, dict):
        return _parse_mist_zip_dict(data, photometry_only=photometry_only)

    # handle raw bytes
    if isinstance(data, bytes):
        typ = _file_type(data)
        if typ is not None:
            if "zip" in typ:
                extracted = extract_zip(data)
                if isinstance(extracted, dict):
                    return _parse_mist_zip_dict(extracted, photometry_only=photometry_only)
                data = extracted
            else:
                data = zlib.decompress(data, 15 + 32)
        if isinstance(data, bytes):
            data = data.decode("utf-8")

    # handle string (file content or path)
    lines = data.split("\n")

    first_line = ""
    for line in lines:
        if line.strip():
            first_line = line.strip()
            break

    if not first_line.startswith("#"):
        return _parse_mist_block_format(lines)

    # fall back to commented header format
    comment_lines = []
    header = None
    header_line = 0
    for num, line in enumerate(lines):
        stripped = line.strip()
        if not stripped:
            continue
        if stripped.startswith("#"):
            comment_lines.append(stripped.lstrip("#").strip())
            header = stripped.lstrip("#").strip().split()
            header_line = num
        else:
            break

    if header is None:
        raise RuntimeError("Could not find a header line in the MIST output.")

    df = pd.read_csv(
        BytesIO(data.encode("utf-8")),
        skiprows=header_line + 1,
        sep=r"\s+",
        names=header,
        comment="#",
    )
    df.attrs["comment"] = "\n".join(comment_lines[:-1])

    return df


def _get_header_columns(text: str) -> list:
    """Extract column names from the header of a MIST isochrone file.

    Works for both the ``#``-commented format and the multi-age block
    format.  Returns the list of column name strings.
    """
    lines = text.split("\n")
    content = [line.split() for line in lines if line.strip()]

    # check for block format (first non-empty line doesn't start with '#')
    first_line = ""
    for line in lines:
        if line.strip():
            first_line = line.strip()
            break

    if not first_line.startswith("#"):
        # block format: find first age block and extract its column header
        for i, row in enumerate(content):
            joined = " ".join(row)
            if "NUMBER" in joined.upper() and "AGE" in joined.upper():
                # scan forward for the first age-block header
                j = i + 1
                while j < len(content):
                    try:
                        float(content[j][0])
                        if len(content[j]) >= 3:
                            float(content[j][1])
                            float(content[j][2])
                            # column header is 2 lines after block header,
                            # first token is '#'
                            hdr = content[j + 2][1:]
                            return hdr
                    except (ValueError, IndexError):
                        pass
                    j += 1
                break
        return []

    # '#'-commented format: last comment line before data is the header
    header = None
    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue
        if stripped.startswith("#"):
            header = stripped.lstrip("#").strip().split()
        else:
            break
    return header if header else []


def _parse_mist_zip_dict(file_dict: dict, photometry_only: bool = False) -> pd.DataFrame | tuple[pd.DataFrame, pd.DataFrame, list]:
    """Parse a MIST zip archive that may contain both theory and photometry files.

    The zip typically contains:
    - A ``.iso`` file with all theory columns
    - A ``.iso.<system>`` file with a subset of theory columns and all
      photometry columns

    Parses both files separately and identifies the photometry-only
    columns by diffing the two headers.

    Parameters
    ----------
    file_dict : dict
        ``{filename: text_content}`` mapping from :func:`extract_zip`.
    photometry_only : bool, optional
        If *True*, return only a ``pd.DataFrame`` of photometry columns
        (columns not in :data:`_MIST_THEORY_COLUMNS`).

    Returns
    -------
    pd.DataFrame or tuple
        * When ``photometry_only=True``: a single ``pd.DataFrame``
          containing only the photometry columns.
        * Otherwise: a 3-tuple ``(theory_df, phot_only_df, phot_columns)``
          where *theory_df* has all non-photometry columns from the
          ``.iso`` file, *phot_only_df* has only the photometry columns,
          and *phot_columns* is the list of photometry column names.
          Either or both DataFrames may be empty if the corresponding
          file was not found in the archive.
    """
    filenames = sorted(file_dict.keys())
    print(f"Zip archive contains: {filenames}")

    # identify the .iso (theory) file and .iso.<system> (photometry) file.
    theory_file = None
    photometry_file = None
    photometry_system = None
    for name in filenames:
        basename = name.split("/")[-1] if "/" in name else name
        if basename.endswith(".iso"):
            theory_file = name
        elif ".iso." in basename:
            photometry_file = name
            photometry_system = basename.split(".iso.")[-1]

    # parse theory file
    if theory_file is not None and not photometry_only:
        print(f"Parsing theory file: {theory_file}")
        theory_df = _parse_single_text(file_dict[theory_file])
    else:
        theory_df = pd.DataFrame()

    # parse photometry file and extract photometry-only columns
    if photometry_file is not None:
        print(f"Parsing photometry file: {photometry_file}")
        phot_df = _parse_single_text(file_dict[photometry_file])

        if photometry_only:
            # only need photometry columns — diff against known theory columns
            phot_only_names = [
                c for c in phot_df.columns if c not in _MIST_THEORY_COLUMNS
            ]
            phot_only_df = phot_df[phot_only_names] if phot_only_names else pd.DataFrame()
            phot_only_df.attrs = phot_df.attrs.copy()
            return phot_only_df

        if theory_file is not None:
            # if theory_df lost its comment (e.g. block format edge case),
            # copy it from phot_df
            if not theory_df.attrs.get("comment") and phot_df.attrs.get("comment"):
                theory_df.attrs["comment"] = phot_df.attrs["comment"]

            theory_cols = set(theory_df.columns)
            phot_only_names = [
                c for c in phot_df.columns
                if c not in theory_cols and c not in _MIST_THEORY_COLUMNS
            ]

            # move any theory columns from the photometry file into
            # the theory DataFrame if they're missing
            cols_to_move = {}
            for c in phot_df.columns:
                if c in _MIST_THEORY_COLUMNS and c not in theory_df.columns:
                    if len(phot_df) == len(theory_df):
                        cols_to_move[c] = phot_df[c].values
                        print(f"  Moving theory column '{c}' from photometry file to theory table.")

            if cols_to_move:
                saved_attrs = theory_df.attrs.copy()
                theory_df = pd.concat(
                    [theory_df, pd.DataFrame(cols_to_move, index=theory_df.index)],
                    axis=1,
                )
                theory_df.attrs.update(saved_attrs)

            print(f"Theory file has {len(theory_df.columns)} columns, "
                  f"photometry file has {len(phot_df.columns)} columns, "
                  f"identified {len(phot_only_names)} photometry-only columns: "
                  f"{phot_only_names}")

            if phot_only_names and len(phot_df) != len(theory_df):
                print(f"WARNING: row count mismatch — theory has {len(theory_df)} "
                      f"rows, photometry has {len(phot_df)} rows.")

            phot_only_df = phot_df[phot_only_names] if phot_only_names else pd.DataFrame()
            if photometry_system:
                phot_only_df.attrs["photometry_system"] = photometry_system
            return theory_df, phot_only_df, phot_only_names

        else:
            # no theory file — treat the photometry file as both
            return phot_df, pd.DataFrame(), []

    elif theory_file is not None:
        print("No photometry file found; parsing theory file only.")
        if photometry_only:
            return pd.DataFrame()
        return theory_df, pd.DataFrame(), []

    else:
        first_name = filenames[0]
        print(f"No .iso file recognized; parsing first file: {first_name}")
        df = _parse_single_text(file_dict[first_name])
        if photometry_only:
            return pd.DataFrame()
        return df, pd.DataFrame(), []


def _parse_single_text(text: str) -> pd.DataFrame:
    """Parse a single MIST isochrone text file into a DataFrame.

    Dispatches to :func:`_parse_mist_block_format` for the multi-age
    block format (first non-blank line does not start with ``#``), or
    parses the ``#``-commented single-table format directly.

    Parameters
    ----------
    text : str
        Full text content of a ``.iso`` or ``.iso.<system>`` file.

    Returns
    -------
    pd.DataFrame
        Parsed data with ``df.attrs["comment"]`` containing the header
        comment text.
    """
    lines = text.split("\n")
    first_line = ""
    for line in lines:
        if line.strip():
            first_line = line.strip()
            break
    if not first_line.startswith("#"):
        return _parse_mist_block_format(lines)

    # '#'-commented format
    comment_lines = []
    header = None
    header_line = 0
    for num, line in enumerate(lines):
        stripped = line.strip()
        if not stripped:
            continue
        if stripped.startswith("#"):
            comment_lines.append(stripped.lstrip("#").strip())
            header = stripped.lstrip("#").strip().split()
            header_line = num
        else:
            break
    if header is None:
        raise RuntimeError("Could not find a header line in the MIST output.")
    df = pd.read_csv(
        BytesIO(text.encode("utf-8")),
        skiprows=header_line + 1,
        sep=r"\s+",
        names=header,
        comment="#",
    )
    df.attrs["comment"] = "\n".join(comment_lines[:-1])
    return df


def _parse_mist_block_format(lines: list) -> pd.DataFrame:
    """Parse the MIST multi-age block isochrone format.

    The format has a short metadata header, then repeated blocks — one per
    isochrone age — each containing its own column-name row.

    Parameters
    ----------
    lines : list of str
        Lines of the MIST isochrone file.

    Returns
    -------
    pd.DataFrame
    """
    import numpy as np

    content = [line.split() for line in lines if line.strip()]

    # collect comment/header lines until the "NUMBER OF AGES" line
    comment_parts = []
    num_ages = None
    header_end = None
    for i, row in enumerate(content):
        joined = " ".join(row)
        if "NUMBER" in joined.upper() and "AGE" in joined.upper():
            num_ages = int(row[-1])
            header_end = i
            break
        comment_parts.append(joined)

    if num_ages is None:
        raise RuntimeError(
            "Could not find 'NUMBER OF AGES' line in MIST block format."
        )

    # age blocks start 2 lines after the "NUMBER OF AGES" line.
    # the first token of the next non-blank line after the num_ages line
    # should be a float (the age value) — scan forward to find it.
    data_start = header_end + 1
    # skip any remaining header lines (e.g., column-count summaries)
    # until reaching the first age-block header.
    # an age-block header line looks like: <age> <num_eeps> <num_cols>
    # where all three are numeric.
    while data_start < len(content):
        try:
            float(content[data_start][0])
            # verify it looks like a block header (at least 3 numeric tokens)
            if len(content[data_start]) >= 3:
                float(content[data_start][1])
                float(content[data_start][2])
                break
        except (ValueError, IndexError):
            pass
        data_start += 1

    data = content[data_start:]

    # parse each age block
    blocks = []
    counter = 0
    hdr_list = None
    for _ in range(num_ages):
        row = data[counter]
        num_eeps = int(row[-2])
        # num_cols = int(row[-1])
        # column names are on the line 2 rows after the block header,
        # prefixed with '#', so skip the '#' token.
        hdr_list = data[counter + 2][1:]

        for eep in range(num_eeps):
            blocks.append(data[3 + counter + eep])

        counter += 3 + num_eeps

    if hdr_list is None:
        raise RuntimeError("Could not parse MIST block format.")

    arr = np.array(blocks, dtype=float)
    df = pd.DataFrame(arr, columns=hdr_list)

    # convert the first column (EEP index) to int
    if hdr_list[0] in df.columns:
        df[hdr_list[0]] = df[hdr_list[0]].astype(int)

    df.attrs["comment"] = "\n".join(comment_parts)
    return df


def get_isochrones(
    age: tuple[float, float, float] | list | float | None = None,
    FeH: float = None,
    alphaFe: Literal[-0.2, 0.0, 0.2, 0.4, 0.6] = None,
    v_div_vcrit: Literal[0.0, 0.4] = None,
    output: str | None = None,
    extinction_Av: float = None,
    version: Literal["MIST1", "MIST2"] = None,
    from_file: str | None = None,
    photometry_only: bool = False,
    **kwargs,
) -> pd.DataFrame:
    """Retrieve MIST isochrones.

    Parameters
    ----------
    age : float, tuple of (low, high, step), list or None
            Age in years or log10(years). A single float queries one isochrone; a tuple of 
            length 3 sets a min, max and step size to query over the corresponding age grid, 
            and a list queries over an age grid.
    FeH : float
        [Fe/H] metallicity value.
    alphaFe : float
        [alpha/Fe] abundance ratio.
    v_div_vcrit : float
        Initial rotation velocity v/v_crit.
    output : str or None
        The name of a photometric system to retrieve synthetic photometry for.
        If None, MIST output is set to "theory".
    extinction_Av : float
        Extinction A_V to apply to photometry.  Has no effect if *photometry* is 
        ``None``.
    version : ``"MIST1"`` or ``"MIST2"``, optional
        MIST version to query.
    from_file : str or None
        If provided, load isochrone data from a file instead of querying the MIST service.
    photometry_only : bool, optional
        If True, only photometry columns are returned.
    **kwargs
        Additional keyword arguments forwarded to the MIST query.

    Returns
    -------
    pd.DataFrame
        Parsed isochrone data.
    """
    if from_file is not None:
        print(f"'from_file' is not None. Loading isochrone data from file: {from_file} " \
                "rather than performing a query.")
        data = load_isochrone(from_file)
        return parse_result(data)

    kw = _cfg['defaults'].copy()
    kw.update(kwargs)

    if v_div_vcrit is not None:
        kw['v_div_vcrit'] = f'vvcrit{v_div_vcrit}'
    if FeH is not None:
        kw['FeH_value'] = str(FeH)
    if extinction_Av is not None:
        kw['Av_value'] = str(extinction_Av)
    if version is not None:
        kw['version'] = version
    if output is not None:
        kw['output_option'] = 'photometry'
        kw['output'] = output
    else:
        print("No synthetic photometry requested; setting MIST output to 'theory'.")
        kw['output_option'] = 'theory'
    if alphaFe is not None:
        n = int(round(abs(alphaFe) * 10))
        kw['alpha_value'] = f'm{n}' if alphaFe < 0 else f'p{n}'

    # check ranges allowed as stated on webform
    _FeH = float(kw.get('FeH_value', 0.0))
    _Av = float(kw.get('Av_value', 0.0))
    if not (-4 <= _FeH <= 0.5):
        raise ValueError(f"FeH must be between -4 and +0.5. Got {_FeH}.")
    if not (0 <= _Av <= 6):
        raise ValueError(f"extinction_Av must be between 0 and 6. Got {_Av}.")

    if age is None:
        kw['age_type'] = 'standard'
        print("'age' is None; using standard MIST age grid.")
    else:
        if isinstance(age, tuple):
            age_min, age_max = age[0], age[1]
        elif isinstance(age, list):
            age_min = min(age)
            age_max = max(age)
        else:
            age_min = age
            age_max = age

        # infer linear or log scale: log10(14.4 Gyr)=10.3
        if age_max <= 10.3:
            if age_min <= 5:
                raise ValueError(f"Age must be > 5 dex (i.e., log10(1e5 yr)) for MIST age interpolation grid. Got {age_min}.")
            kw['age_scale'] = 'log10'
        else:
            if age_min <= 1e5:
                raise ValueError(f"Age must be > 1e5 yr for MIST age interpolation grid. Got {age_min}.")
            kw['age_scale'] = 'linear'
        print(f"Inferred {kw['age_scale']} age scale based on age values {age}.")

        if isinstance(age, (float, int)):
            kw['age_type'] = 'single'
            kw['age_value'] = str(age)

        elif isinstance(age, tuple):
            if len(age) != 3:
                raise ValueError(
                    f"age as a tuple must have 3 elements "
                    f"(low, high, step), got {len(age)}."
                )
            kw['age_type'] = 'range'
            for key, val in zip(
                ('age_range_low', 'age_range_high', 'age_range_delta'),
                age, strict=False,
            ):
                kw[key] = str(val)

        elif isinstance(age, list):
            kw['age_type'] = 'list'
            kw['age_value'] = " ".join(map(str, age))

        else:
            raise ValueError("Invalid age parameter. Must be a float, tuple, list, or None.")

    d = _build_query(**kw)
    res = query(d)

    return parse_result(res, photometry_only=photometry_only)
