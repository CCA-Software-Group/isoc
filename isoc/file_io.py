import io
import zipfile
import os

from ezpadova.tools import get_file_archive_type

def extract_zip(zip_bytes):
    """ Extract the content of a zip file

    Parameters
    ----------
    zip_bytes: bytes
        string that contains the binary code

    Returns
    -------
    content:str
        ascii string contained in the zip code.
    """
    fp = zipfile.ZipFile(io.BytesIO(zip_bytes))
    data = {name: fp.read(name) for name in fp.namelist()}
    if len(data) > 1:
        return data
    else:
        return data[list(data.keys())[0]]
    

def load_isochrone(filepath: str) -> str:
    if not os.path.isfile(filepath):
        raise FileNotFoundError(f"File not found at path {filepath}")

    typ = get_file_archive_type(filepath, stream=False)
    if typ is not None and "zip" in typ:
        with open(filepath, "rb") as fh:
            data = extract_zip(fh.read())
    elif typ is not None:  # gz / bz2
        import gzip
        with gzip.open(filepath, "rb") as fh:
            data = fh.read()
    else:
        with open(filepath, "r") as fh:
            data = fh.read()
            
    return data
