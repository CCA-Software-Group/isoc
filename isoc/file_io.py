import io
import os
import zipfile

from ezpadova.tools import get_file_archive_type


def extract_zip(data: bytes) -> dict:
    """Extract all files from a zip archive stored in *data*.

    Parameters
    ----------
    data : bytes
        Raw bytes of a zip archive.

    Returns
    -------
    dict
        Mapping of ``{filename: content_string}`` for every file in the
        archive.  Text files are decoded as UTF-8; binary files are
        returned as raw bytes.
    """
    zf = zipfile.ZipFile(io.BytesIO(data))
    result = {}
    for name in zf.namelist():
        raw = zf.read(name)
        try:
            result[name] = raw.decode("utf-8")
        except UnicodeDecodeError:
            result[name] = raw
    return result

def load_isochrone(filepath: str) -> str | bytes | dict:
    """Load raw isochrone data from a local file.

    If the file type is:

    * **zip archive** – extracted with :func:`extract_zip`, returns a
      ``dict`` mapping ``{filename: content}``.
    * **gzip/bz2 archive** – decompressed, returns raw ``bytes``.
    * **plain text** – read as UTF-8, returns a ``str``.

    Parameters
    ----------
    filepath : str
        Path to the local isochrone file.

    Returns
    -------
    str, bytes, or dict
        The file contents in whichever form matches the archive type.

    Raises
    ------
    FileNotFoundError
        If *filepath* does not point to an existing file.
    """
    if not os.path.isfile(filepath):
        raise FileNotFoundError(f"File not found at path {filepath}")

    typ = get_file_archive_type(filepath, stream=False)
    if typ is not None and "zip" in typ:
        with open(filepath, "rb") as fh:
            data = extract_zip(fh.read())
    elif typ is not None:
        import gzip
        with gzip.open(filepath, "rb") as fh:
            data = fh.read()
    else:
        with open(filepath) as fh:
            data = fh.read()

    return data
