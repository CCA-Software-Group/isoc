from io import BytesIO
from typing import Literal, Tuple, Union
import zlib
import re
from bs4 import BeautifulSoup

import pandas as pd
import requests

from .mist_config import configuration as _cfg
from .file_io import load_isochrone, extract_zip


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
    sequence is found, otherwise ``None``.  Mirrors the detection in
    ``ezmist.file_type``.
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


def query(q: str) -> bytes:
    """Query the MIST webpage with the given parameters.

    This function sends a POST request to the MIST webpage specified in the
    configuration and retrieves the resulting data. The data is then processed
    and returned as bytes. If the server response is incorrect or if there is
    an issue with the data retrieval, a RuntimeError is raised.

    Args:
        q: URL-encoded query string.

    Returns:
        bytes: The retrieved data from the MIST webpage.

    Raises:
        RuntimeError: If the server response is incorrect or if there is an
                      issue with data retrieval.
    """
    url = _cfg["request_url"]
    # Use HTTPS to avoid HTTP -> HTTPS redirects that drop POST body
    if url.startswith("http://"):
        url = url.replace("http://", "https://", 1)
    print(f"Querying {url}.")
    c = requests.post(
        url,
        data=q.encode('utf8'),
        headers={'Content-Type': 'application/x-www-form-urlencoded'},
        timeout=120,
    ).text

    # Extract download link from server response
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

    # Build download URL from the site root
    base_url = re.match(r'https?://[^/]+', url).group(0)
    if fname.startswith("http"):
        data_url = fname
    elif fname.startswith("/"):
        data_url = base_url + fname
    else:
        data_url = base_url + "/" + fname

    print(f"Downloading data...{data_url}")
    r = requests.get(data_url, timeout=120).content
    typ = _file_type(r)
    if typ is not None:
        if 'zip' in typ:
            r = extract_zip(bytes(r))
            # extract_zip returns a dict when the zip has multiple files;
            # take the first (or only) file's content.
            if isinstance(r, dict):
                r = list(r.values())[0]
        else:
            r = zlib.decompress(bytes(r), 15 + 32)
    return r


def parse_result(data: Union[str, bytes]) -> pd.DataFrame:
    """Parse MIST isochrone data and return a pandas DataFrame.

    *data* may be:

    * **bytes** – raw content returned by the MIST server (possibly
      gzip- or zip-compressed).
    * **str that is a file path** – a local ``.txt``, ``.dat``, ``.gz``,
      or ``.zip`` file containing isochrone data.
    * **str of file content** – the decoded text of an isochrone file.

    Parameters
    ----------
    data : str or bytes
        Raw server content, a file path, or decoded text.

    Returns
    -------
    pd.DataFrame
        A DataFrame containing the parsed isochrone data.  The comment
        lines from the file header are stored in ``df.attrs["comment"]``.
    """
    # decode webform response
    if isinstance(data, bytes):
        typ = _file_type(data)
        if typ is not None:
            if "zip" in typ:
                data = extract_zip(data)
            else:
                data = zlib.decompress(data, 15 + 32)
        if isinstance(data, bytes):
            data = data.decode("utf-8")

    lines = data.split("\n")

    # Detect format: MIST isochrone files start with a header block
    # (MIST version, MESA revision, etc.) followed by age blocks,
    # each with its own column header line prefixed by '#'.
    # Alternatively, simple '#'-commented CSV-like files are supported.

    # Try MIST multi-age block format (as used by ezmist)
    # Check if the first non-empty line does NOT start with '#'
    first_line = ""
    for line in lines:
        if line.strip():
            first_line = line.strip()
            break

    if not first_line.startswith("#"):
        # MIST block format: parse like ezmist's _read_mist_iso_filecontent
        return _parse_mist_block_format(lines)

    # Fall back to '#'-commented header format
    comment_lines = []
    header = None
    header_line = 0
    for num, line in enumerate(lines):
        stripped = line.strip()
        if not stripped:
            continue
        if stripped.startswith("#"):
            comment_lines.append(stripped.lstrip("#").strip())
            # last comment line before data is column header
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


def _parse_mist_block_format(lines: list) -> pd.DataFrame:
    """Parse the MIST multi-age block isochrone format.

    This mirrors the parsing logic in ``ezmist._read_mist_iso_filecontent``.
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

    # Global header: lines 0–6
    # line 0: MIST version
    # line 1: MESA revision
    # line 3: abundance labels
    # line 4: abundance values + rotation
    # line 6: number of ages
    comment_parts = []
    comment_parts.append(" ".join(content[0]))
    comment_parts.append(" ".join(content[1]))

    num_ages = int(content[6][-1])

    # Parse each age block starting at content[8:]
    blocks = []
    counter = 0
    data = content[8:]

    hdr_list = None
    for _ in range(num_ages):
        row = data[counter]
        num_eeps = int(row[-2])
        num_cols = int(row[-1])
        # Column names are on the line 2 rows after the block header,
        # prefixed with '#', so skip the '#' token.
        hdr_list = data[counter + 2][1:]

        for eep in range(num_eeps):
            blocks.append(data[3 + counter + eep])

        counter += 3 + num_eeps + 2

    if hdr_list is None:
        raise RuntimeError("Could not parse MIST block format.")

    arr = np.array(blocks, dtype=float)
    df = pd.DataFrame(arr, columns=hdr_list)

    # Convert the first column (EEP index) to int
    if hdr_list[0] in df.columns:
        df[hdr_list[0]] = df[hdr_list[0]].astype(int)

    df.attrs["comment"] = "\n".join(comment_parts)

    return df


def get_isochrones(
    age: Union[Tuple[float, float, float], list, float, None] = None,
    FeH: float = 0.0,
    alphaFe: Literal[-0.2, 0.0, 0.2, 0.4, 0.6] = 0.0,
    v_vcrit: float = 0.4,
    mist_version: Literal["MIST1", "MIST2"] = "MIST1",
    output_type: Literal["theory", "photometry"] = "theory",
    extinction_Av: float = 0.0,
    from_file: Union[str, None] = None,
    **kwargs,
) -> pd.DataFrame:
    """Retrieve MIST isochrones.

    Parameters
    ----------
    age : float, tuple of (low, high, step), list or None
        Age in years or log10(years). A single float queries one isochrone; otherwise 
        multiple isochrones are queried.
    FeH : float
        [Fe/H] metallicity value.
    alphaFe : float
        [alpha/Fe] abundance ratio.
    v_vcrit : float
        Initial rotation velocity v/v_crit.
    mist_version : float
        MIST version to query
    output_type : str
        Type of output to retrieve: "theory" or "photometry").
    extinction_Av : float
        Extinction in magnitudes (A_V).
    from_file : str or None
        If provided, load isochrone data from a file instead of querying the MIST service.
    **kwargs
        Additional keyword arguments forwarded to the MIST query.

    Returns
    -------
    pd.DataFrame
        Parsed isochrone data.
    """
    if from_file is not None:
        print(f"Loading MIST isochrone data from file: {from_file}")
        data = load_isochrone(from_file)
        return parse_result(data)
    
    assert -4 <= FeH <= 0.5, f"FeH must be between -4 and +0.5. Got {FeH}."
    assert 0 <= extinction_Av <= 6, f"extinction_Av must be between 0 and 6. Got {extinction_Av}."

    kw = _cfg['defaults'].copy()
    kw.update(kwargs)

    kw['v_div_vcrit'] = f'vvcrit{v_vcrit}'
    kw['FeH_value'] = str(FeH)
    kw['Av_value'] = str(extinction_Av)
    kw['version'] = mist_version
    kw['output_option'] = output_type    
    if alphaFe >= 0:
        kw['afe'] = f'afep{abs(alphaFe)}'
    else:
        kw['afe'] = f'afem{abs(alphaFe)}'

    if age is None: 
        kw['age_type'] = 'standard'
    else:
        age_max = max(age) if isinstance(age, (list, tuple)) else age
        # infer linear or log scale: log10(14.4 Gyr) = 10.3
        if age_max <= 10.3:
            kw['age_scale'] = 'log10'
            print("Inferred log10 age scale based on age values.")
        else:
            kw['age_scale'] = 'linear'
            print("Inferred linear age scale based on age values.")
            
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
                age,
            ):
                kw[key] = str(val)

        elif isinstance(age, list):
            kw['age_type'] = 'list'
            kw['age_value'] = " ".join(map(str, age))

        else:
            raise ValueError("Invalid age parameter. Must be a float, tuple, list, or None.")

    d = _build_query(**kw)
    res = query(d)

    return parse_result(res)