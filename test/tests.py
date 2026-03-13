import numpy as np
import pytest

from isoc import mist_config
from isoc.isochrone import Isochrone
from isoc.plot import plot_color_magnitude, plot_isochrone


## test loading and parsing local isochrone files
class TestLocalFiles:
    def test_padova_single_has_data(self, data_dir):
        padova_single = Isochrone.from_padova(from_file=str(data_dir / "padova_single.dat"))
        assert len(padova_single) > 0
        assert padova_single.database == "padova"

    def test_padova_grid_has_data(self, data_dir):
        padova_grid = Isochrone.from_padova(from_file=str(data_dir / "padova_multiple.dat"))
        assert len(padova_grid) > 0
        assert padova_grid.database == "padova"
        assert padova_grid.n_isochrones >= 2

    def test_mist_single_has_data(self, data_dir):
        mist_single = Isochrone.from_mist(from_file=str(data_dir / "mist_single.zip"))
        assert len(mist_single) > 0
        assert mist_single.database == "mist"

    def test_mist_grid_has_data(self, data_dir):
        mist_grid = Isochrone.from_mist(from_file=str(data_dir / "mist_multiple.zip"))
        assert len(mist_grid) > 0
        assert mist_grid.database == "mist"
        assert mist_grid.n_isochrones >= 2


## test data presence and database correctness
class TestFromPadova:
    def test_has_data(self, padova_iso):
        assert len(padova_iso) > 0

    def test_database(self, padova_iso):
        assert padova_iso.database == "padova"

class TestFromMist:
    def test_has_data(self, mist_iso):
        assert len(mist_iso) > 0

    def test_database(self, mist_iso):
        assert mist_iso.database == "mist"

class TestQueryEzpadova:
    def test_has_data(self, ezpadova_iso):
        assert len(ezpadova_iso) > 0

    def test_database(self, ezpadova_iso):
        assert ezpadova_iso.database == "padova"


## test grid contains multiple isochrones, with properties present for each
class TestGridPadova:
    def test_has_data(self, padova_grid):
        assert len(padova_grid) > 0

    def test_multiple_ages(self, padova_grid):
        assert padova_grid.n_isochrones >= 2

    def test_properties_accessible(self, padova_grid):
        assert len(padova_grid.log_Teff) == len(padova_grid)
        assert len(padova_grid.log_L) == len(padova_grid)
        assert len(padova_grid.mass) == len(padova_grid)

class TestGridMist:
    def test_has_data(self, mist_grid):
        assert len(mist_grid) > 0

    def test_multiple_ages(self, mist_grid):
        assert mist_grid.n_isochrones >= 2

    def test_properties_accessible(self, mist_grid):
        assert len(mist_grid.log_Teff) == len(mist_grid)
        assert len(mist_grid.log_L) == len(mist_grid)
        assert len(mist_grid.mass) == len(mist_grid)


## test isochrone properties presence
class TestIsochroneProperties:
    """Verify that every @property on Isochrone is accessible."""

    _expected_properties = [
        "database",
        "data",
        "photometry",
        "columns",
        "n_isochrones",
        "isochrone",
        "metallicity_type",
        "log_Teff",
        "log_L",
        "log_g",
        "initial_mass",
        "mass",
        "log_age",
        "metallicity",
        "query_parameters",
        "header",
    ]

    @pytest.mark.parametrize("prop", _expected_properties)
    def test_padova_property_exists(self, padova_iso, prop):
        val = getattr(padova_iso, prop)
        assert val is not None

    @pytest.mark.parametrize("prop", _expected_properties)
    def test_mist_property_exists(self, mist_iso, prop):
        val = getattr(mist_iso, prop)
        assert val is not None

    @pytest.mark.parametrize("prop", _expected_properties)
    def test_padova_grid_property_exists(self, padova_grid, prop):
        val = getattr(padova_grid, prop)
        assert val is not None

    @pytest.mark.parametrize("prop", _expected_properties)
    def test_mist_grid_property_exists(self, mist_grid, prop):
        val = getattr(mist_grid, prop)
        assert val is not None


## test header presence and content
class TestHeader:
    def test_padova_header_is_string(self, padova_iso):
        h = padova_iso.header
        assert isinstance(h, str)
        assert len(h) > 0

    def test_mist_header_is_string(self, mist_iso):
        h = mist_iso.header
        assert isinstance(h, str)
        assert len(h) > 0

    def test_header_displays_newlines(self, padova_iso):
        h = padova_iso.header
        assert "\n" in h
        # repr should also show real newlines (via _DisplayStr)
        assert "\\n" not in repr(h)

    def test_mist_header_no_trailing_numbers(self, mist_iso):
        """MIST headers have trailing lines of column numbers."""
        h = mist_iso.header
        last_line = h.strip().split("\n")[-1]
        tokens = last_line.strip().split()
        assert not all(_is_numeric(t) for t in tokens), (
            f"Last header line is all numbers: {last_line!r}"
        )


## test photometry structure
class TestPhotometry:
    def test_data_is_dict_padova(self, padova_iso):
        d = padova_iso.photometry.data
        assert isinstance(d, dict)
        assert len(d) > 0

    def test_data_is_dict_mist(self, mist_iso):
        d = mist_iso.photometry.data
        assert isinstance(d, dict)
        assert len(d) > 0

    def test_columns_is_dict_padova(self, padova_iso):
        cols = padova_iso.photometry.columns
        assert isinstance(cols, dict)
        for _, col_list in cols.items():
            assert isinstance(col_list, list)
            assert len(col_list) > 0

    def test_columns_is_dict_mist(self, mist_iso):
        cols = mist_iso.photometry.columns
        assert isinstance(cols, dict)
        for _, col_list in cols.items():
            assert isinstance(col_list, list)
            assert len(col_list) > 0

    def test_systems_padova(self, padova_iso):
        systems = padova_iso.photometry.systems
        assert isinstance(systems, dict)
        assert len(systems) > 0

    def test_systems_mist(self, mist_iso):
        systems = mist_iso.photometry.systems
        assert isinstance(systems, dict)
        assert len(systems) > 0

    def test_available_systems_padova(self, padova_iso):
        systems = padova_iso.photometry.available_systems
        assert isinstance(systems, dict)
        assert len(systems) > 0

    def test_available_systems_mist(self, mist_iso):
        systems = mist_iso.photometry.available_systems
        assert isinstance(systems, dict)
        assert len(systems) > 0

    def test_repr(self, padova_iso):
        r = repr(padova_iso.photometry)
        assert "Photometry" in r
        assert "system(s)" in r

    def test_band_attribute_access_padova(self, padova_iso):
        """Access a band via attribute on Photometry."""
        cols = padova_iso.photometry.columns
        first_system = next(iter(cols))
        first_band = cols[first_system][0]
        val = padova_iso.photometry.data[first_system][first_band]
        assert len(val) == len(padova_iso)

    def test_band_attribute_access_mist(self, mist_iso):
        cols = mist_iso.photometry.columns
        first_system = next(iter(cols))
        first_band = cols[first_system][0]
        val = mist_iso.photometry.data[first_system][first_band]
        assert len(val) == len(mist_iso)

    def test_grid_photometry_padova(self, padova_grid):
        cols = padova_grid.photometry.columns
        assert isinstance(cols, dict)
        assert len(cols) > 0

    def test_grid_photometry_mist(self, mist_grid):
        cols = mist_grid.photometry.columns
        assert isinstance(cols, dict)
        assert len(cols) > 0


## test photometry header
class TestPhotometryHeader:
    def test_padova_photometry_header(self, padova_iso):
        h = padova_iso.photometry.header
        assert isinstance(h, str)
        assert "PHOTOMETRY." in h
        assert len(h) > 0

    def test_mist_photometry_header(self, mist_iso):
        h = mist_iso.photometry.header
        assert isinstance(h, str)
        assert "PHOTOMETRY." in h
        assert len(h) > 0


## test color calculation
class TestGetColor:
    def _first_two_bands(self, iso):
        cols = iso.photometry.columns
        first_system = next(iter(cols))
        bands = cols[first_system]
        if len(bands) < 2:
            pytest.skip("Not enough photometry bands")
        return bands[0], bands[1]

    def test_color_computed_padova(self, padova_iso):
        b1, b2 = self._first_two_bands(padova_iso)
        color = padova_iso.photometry.get_color(b1, b2)
        assert len(color) == len(padova_iso)
        assert np.all(np.isfinite(color.value))

    def test_color_computed_mist(self, mist_iso):
        b1, b2 = self._first_two_bands(mist_iso)
        color = mist_iso.photometry.get_color(b1, b2)
        assert len(color) == len(mist_iso)

    def test_color_added_to_table(self, padova_iso):
        b1, b2 = self._first_two_bands(padova_iso)
        padova_iso.photometry.get_color(b1, b2)
        color_name = f"{b1}-{b2}"
        # check the color column exists in the system's QTable
        cols = padova_iso.photometry.columns
        first_system = next(iter(cols))
        assert color_name in cols[first_system]

    def test_color_grid_padova(self, padova_grid):
        b1, b2 = self._first_two_bands(padova_grid)
        color = padova_grid.photometry.get_color(b1, b2)
        assert len(color) == len(padova_grid)

    def test_color_grid_mist(self, mist_grid):
        b1, b2 = self._first_two_bands(mist_grid)
        color = mist_grid.photometry.get_color(b1, b2)
        assert len(color) == len(mist_grid)


## test defaults and allowed query values
class TestStaticMethods:
    def test_mist_defaults(self):
        defaults = Isochrone.default_values(database="mist")
        assert isinstance(defaults, dict)
        assert "_aliases" in defaults

    def test_padova_defaults(self):
        defaults = Isochrone.default_values(database="padova")
        assert isinstance(defaults, dict)
        assert "_aliases" in defaults


## test alternate names for photometry systems
class TestPhotometrySystemResolution:
    def test_padova_resolve_long_description(self):
        tmp = Isochrone(database="padova")
        systems = tmp.photometry.available_systems
        short_key = next(iter(systems))
        long_desc = systems[short_key]
        resolved = Isochrone._resolve_photometry_system(long_desc, "padova")
        assert resolved == short_key

    def test_mist_resolve_long_description(self):
        tmp = Isochrone(database="mist")
        systems = tmp.photometry.available_systems
        short_key = next(iter(systems))
        long_desc = systems[short_key]
        resolved = Isochrone._resolve_photometry_system(long_desc, "mist")
        assert resolved == short_key

    def test_resolve_none_returns_none(self):
        assert Isochrone._resolve_photometry_system(None, "mist") is None

    def test_resolve_invalid_raises(self):
        with pytest.raises(ValueError):
            Isochrone._resolve_photometry_system("not_a_real_system", "padova")


## test updating files holding current MIST database parameters
class TestMistConfig:
    def test_update_config(self):
        mist_config.update_config()
        assert mist_config.configuration["defaults"]
        assert "version" in mist_config.configuration


## test plotting isochrones
class TestPlotIsochrone:
    def test_plot_single_padova(self, padova_iso):
        fig, ax = plot_isochrone(padova_iso)
        assert ax.has_data()

    def test_plot_single_mist(self, mist_iso):
        fig, ax = plot_isochrone(mist_iso)
        assert ax.has_data()

    def test_plot_multiple(self, padova_iso, mist_iso):
        fig, ax = plot_isochrone(
            [padova_iso, mist_iso],
            iso_labels=["Padova", "MIST"],
        )
        assert ax.has_data()
        assert ax.get_legend() is not None

    def test_plot_custom_axes(self, padova_iso):
        fig, ax = plot_isochrone(padova_iso, x="log_Teff", y="log_g")
        assert ax.has_data()

    def test_plot_no_invert(self, padova_iso):
        fig, ax = plot_isochrone(padova_iso, invert_x=False)
        assert not ax.xaxis_inverted()

    def test_plot_grid_padova(self, padova_grid):
        fig, ax = plot_isochrone(padova_grid)
        assert ax.has_data()

    def test_plot_grid_mist(self, mist_grid):
        fig, ax = plot_isochrone(mist_grid)
        assert ax.has_data()


## test plotting color-magnitude diagrams
class TestPlotColorMagnitude:
    def _first_two_bands(self, iso):
        cols = iso.photometry.columns
        first_system = next(iter(cols))
        bands = cols[first_system]
        if len(bands) < 2:
            pytest.skip("Not enough photometry bands")
        return bands[0], bands[1]

    def test_cmd_padova(self, padova_iso):
        b1, b2 = self._first_two_bands(padova_iso)
        fig, ax = plot_color_magnitude(padova_iso, b1, b2)
        assert ax.has_data()

    def test_cmd_mist(self, mist_iso):
        b1, b2 = self._first_two_bands(mist_iso)
        fig, ax = plot_color_magnitude(mist_iso, b1, b2)
        assert ax.has_data()

    def test_cmd_custom_mag(self, padova_iso):
        b1, b2 = self._first_two_bands(padova_iso)
        fig, ax = plot_color_magnitude(padova_iso, b1, b2, mag=b2)
        assert ax.has_data()

    def test_cmd_grid_padova(self, padova_grid):
        b1, b2 = self._first_two_bands(padova_grid)
        fig, ax = plot_color_magnitude(padova_grid, b1, b2)
        assert ax.has_data()

    def test_cmd_grid_mist(self, mist_grid):
        b1, b2 = self._first_two_bands(mist_grid)
        fig, ax = plot_color_magnitude(mist_grid, b1, b2)
        assert ax.has_data()


## test adding additional photometry systems to existing isochrones
class TestAddPhotometry:
    def test_add_photometry_padova(self, padova_iso):
        n_systems_before = len(padova_iso.photometry.systems)
        cols_before = list(padova_iso.data.colnames)
        nrows_before = len(padova_iso)
        padova_iso.photometry.add_photometry("2mass_spitzer")
        n_systems_after = len(padova_iso.photometry.systems)
        assert n_systems_after == n_systems_before + 1
        # theory data should be unchanged
        assert len(padova_iso) == nrows_before
        assert list(padova_iso.data.colnames) == cols_before

    def test_add_photometry_mist(self, mist_iso):
        n_systems_before = len(mist_iso.photometry.systems)
        cols_before = list(mist_iso.data.colnames)
        nrows_before = len(mist_iso)
        mist_iso.photometry.add_photometry("LSST")
        n_systems_after = len(mist_iso.photometry.systems)
        assert n_systems_after == n_systems_before + 1
        # theory data should be unchanged
        assert len(mist_iso) == nrows_before
        assert list(mist_iso.data.colnames) == cols_before

    def test_duplicate_system_skipped(self, padova_iso):
        """Adding the same system twice should not create a new entry."""
        n_before = len(padova_iso.photometry.systems)
        padova_iso.photometry.add_photometry("2mass_spitzer")
        assert len(padova_iso.photometry.systems) == n_before

    def test_header_after_add(self, mist_iso):
        """After add_photometry the header should list both systems."""
        h = mist_iso.photometry.header
        assert "PHOTOMETRY." in h
        # should have at least 2 `PHOTOMETRY.` sections
        assert h.count("PHOTOMETRY.") >= 2


## test Photometry.__getitem__ and _PhotometryTables column access
class TestPhotometryDataAccess:
    def test_data_columns_matches_photometry_columns(self, padova_iso):
        assert padova_iso.photometry.data.columns == padova_iso.photometry.columns

    def test_data_columns_is_dict(self, mist_iso):
        cols = mist_iso.photometry.data.columns
        assert isinstance(cols, dict)
        assert len(cols) > 0

    def test_data_system_access_returns_qtable(self, mist_iso):
        from astropy.table import QTable
        full_name = next(iter(mist_iso.photometry.systems.values()))
        tbl = mist_iso.photometry.data[full_name]
        assert isinstance(tbl, QTable)

    def test_data_band_access_returns_column(self, padova_iso):
        cols = padova_iso.photometry.columns
        first_sys = next(iter(cols))
        first_band = cols[first_sys][0]
        col = padova_iso.photometry.data[first_sys][first_band]
        assert len(col) == len(padova_iso)

    def test_photometry_getitem_band(self, mist_iso):
        cols = mist_iso.photometry.columns
        first_sys = next(iter(cols))
        first_band = cols[first_sys][0]
        col = mist_iso.photometry[first_sys][first_band]
        assert len(col) == len(mist_iso)

    def test_photometry_getitem_system_returns_qtable(self, padova_iso):
        from astropy.table import QTable
        full_name = next(iter(padova_iso.photometry.systems.values()))
        tbl = padova_iso.photometry[full_name]
        assert isinstance(tbl, QTable)

    def test_photometry_getitem_ambiguous_raises(self, mist_iso):
        """A band present in multiple systems should raise ValueError."""
        from collections import Counter
        all_cols = list(mist_iso.photometry.columns.values())
        counter = Counter(c for band_list in all_cols for c in band_list)
        ambiguous = [c for c, n in counter.items() if n > 1]
        if not ambiguous:
            pytest.skip("No ambiguous columns present (only one system loaded)")
        with pytest.raises(ValueError):
            mist_iso.photometry[ambiguous[0]]


## test _IsochroneIndex (Isochrone.isochrone)
class TestIsochroneIndex:
    def test_len_matches_n_isochrones_padova(self, padova_grid):
        assert len(padova_grid.isochrone) == padova_grid.n_isochrones

    def test_len_matches_n_isochrones_mist(self, mist_grid):
        assert len(mist_grid.isochrone) == mist_grid.n_isochrones

    def test_int_index_returns_isochrone(self, padova_grid):
        sub = padova_grid.isochrone[0]
        assert isinstance(sub, Isochrone)

    def test_int_index_negative(self, mist_grid):
        last = mist_grid.isochrone[-1]
        assert isinstance(last, Isochrone)
        assert len(last) > 0

    def test_int_index_last_equals_negative_one(self, mist_grid):
        n = len(mist_grid.isochrone)
        assert len(mist_grid.isochrone[n - 1]) == len(mist_grid.isochrone[-1])

    def test_int_index_out_of_range(self, padova_grid):
        n = len(padova_grid.isochrone)
        with pytest.raises(IndexError):
            padova_grid.isochrone[n]

    def test_subset_row_sum_equals_total(self, mist_grid):
        total = sum(len(sub) for sub in mist_grid.isochrone)
        assert total == len(mist_grid)

    def test_subset_preserves_database(self, padova_grid):
        sub = padova_grid.isochrone[0]
        assert sub.database == padova_grid.database

    def test_subset_preserves_photometry_systems(self, mist_grid):
        sub = mist_grid.isochrone[0]
        assert sub.photometry.systems == mist_grid.photometry.systems

    def test_subset_photometry_row_count(self, mist_grid):
        sub = mist_grid.isochrone[0]
        for _full_name, tbl in sub.photometry._tables.items():
            assert len(tbl) == len(sub)

    def test_string_key_exact_label(self, padova_grid):
        label = padova_grid.isochrone.labels[0]
        sub = padova_grid.isochrone[label]
        assert isinstance(sub, Isochrone)
        assert len(sub) == len(padova_grid.isochrone[0])

    def test_string_key_field_value_column(self, data_dir):
        """Use a raw column name (not an alias) as the field key."""
        iso = Isochrone.from_mist(from_file=str(data_dir / "mist_multiple.zip"))
        sub = iso.isochrone["log10_isochrone_age_yr=9"]
        assert len(sub) > 0

    def test_string_key_unknown_field_raises(self, padova_grid):
        with pytest.raises(KeyError):
            padova_grid.isochrone["not_a_real_column=0"]

    def test_string_key_no_match_raises(self, mist_grid):
        with pytest.raises(KeyError):
            mist_grid.isochrone["log_age=999"]

    def test_string_key_bad_format_raises(self, padova_grid):
        with pytest.raises(KeyError):
            padova_grid.isochrone["not_a_valid_key"]

    def test_labels_length(self, mist_grid):
        labels = mist_grid.isochrone.labels
        assert len(labels) == len(mist_grid.isochrone)

    def test_labels_are_strings_with_equals(self, padova_grid):
        for label in padova_grid.isochrone.labels:
            assert isinstance(label, str)
            assert "=" in label

    def test_iteration_yields_isochrones(self, padova_grid):
        for sub in padova_grid.isochrone:
            assert isinstance(sub, Isochrone)

    def test_iteration_row_sum(self, mist_grid):
        total = sum(len(sub) for sub in mist_grid.isochrone)
        assert total == len(mist_grid)

    def test_repr_contains_class_name(self, padova_grid):
        assert "IsochroneIndex" in repr(padova_grid.isochrone)

    def test_local_padova_n_groups(self, data_dir):
        iso = Isochrone.from_padova(from_file=str(data_dir / "padova_multiple.dat"))
        # padova_multiple.dat: 2 ages × 3 metallicities = 6 isochrones
        assert len(iso.isochrone) == 6

    def test_local_mist_n_groups(self, data_dir):
        iso = Isochrone.from_mist(from_file=str(data_dir / "mist_multiple.zip"))
        # mist_multiple.zip: 3 ages, 1 metallicity
        assert len(iso.isochrone) == 3

    def test_local_mist_subset_rows_correct(self, data_dir):
        iso = Isochrone.from_mist(from_file=str(data_dir / "mist_multiple.zip"))
        sub = iso.isochrone["log_age=9"]
        ages = np.asarray(sub.log_age)
        if hasattr(ages, "value"):
            ages = ages.value
        assert np.all(np.isclose(ages, 9.0))

    def test_plot_with_isochrone_index(self, mist_grid):
        """_IsochroneIndex should be passable directly to plot_isochrone."""
        from isoc.plot import plot_isochrone
        fig, ax = plot_isochrone(mist_grid.isochrone, iso_labels=mist_grid.isochrone.labels)
        assert ax.has_data()


def _is_numeric(s: str) -> bool:
    try:
        float(s)
        return True
    except ValueError:
        return False
