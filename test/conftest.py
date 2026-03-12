from pathlib import Path

import matplotlib
import pytest

matplotlib.use("Agg")
import matplotlib.pyplot as plt

from isoc.isochrone import Isochrone


@pytest.fixture(autouse=True)
def _close_figures():
    """Close all matplotlib figures after each test."""
    yield
    plt.close("all")

@pytest.fixture(scope="session")
def data_dir(pytestconfig):
    return Path(pytestconfig.rootdir) / "docs" / "data_files"


@pytest.fixture(scope="module")
def padova_iso():
    return Isochrone.from_padova(
        age=1e9, metallicity=0.02, metallicity_type="Z",
        photometry="ubvrijhk",
    )

@pytest.fixture(scope="module")
def mist_iso():
    return Isochrone.from_mist(
        age=9, metallicity=0.1, photometry="UBVRIplus",
        extinction=1,
    )

@pytest.fixture(scope="module")
def ezpadova_iso():
    return Isochrone.query_ezpadova(default_ranges=True)


@pytest.fixture(scope="module")
def padova_grid():
    """Padova grid: 3 ages at fixed Z."""
    return Isochrone.from_padova(
        age=(1e8, 1e10, 5e9),
        metallicity=0.02, metallicity_type="Z",
        photometry="ubvrijhk",
    )

@pytest.fixture(scope="module")
def mist_grid():
    """MIST grid: 3 ages at fixed [Fe/H]."""
    return Isochrone.from_mist(
        age=(8.0, 10.0, 1.0),
        metallicity=0.1, photometry="UBVRIplus",
    )
