"""Convenience plotting functions for isochrone data. All functions return ``(fig, ax)`` tuples.
"""
from collections.abc import Sequence

import matplotlib.pyplot as plt
import numpy as np
from astropy import units as u
from matplotlib.axes import Axes
from matplotlib.figure import Figure

from .isochrone import Isochrone

__all__ = [
    "plot_isochrone",
    "plot_color_magnitude",
]


def plot_isochrone(
    iso: Isochrone | Sequence[Isochrone],
    iso_labels: Sequence[str] | None = None,
    x: str = "log_Teff",
    y: str = "log_L",
    fig: Figure | None = None,
    ax: Axes | None = None,
    invert_x: bool = True,
    cmap: str = "viridis",
    **kwargs,
) -> tuple[Figure, Axes]:
    """Plot one or more isochrones on an HR diagram.

    Parameters
    ----------
    iso : Isochrone or sequence of Isochrone
        Isochrone object(s) to plot.
    iso_labels : sequence of str, optional
        Legend labels, one per isochrone.  If *None* no legend is added.
        Ignored when *iso* is a single Isochrone.
    x, y : str
        Property or column names for the horizontal and vertical axes.
        Recognised shortcuts: ``"log_Teff"``, ``"log_L"``, ``"log_g"``,
        ``"mass"``, or any column name in ``iso.data``.
    fig : matplotlib Figure, optional
        Existing figure to draw on.  A new axes is added to it when *ax*
        is ``None``.  Ignored if *ax* is provided.
    ax : matplotlib Axes, optional
        Existing axes to draw on.  Takes priority over *fig*.  A new
        figure is created if both are ``None``.
    invert_x : bool
        If *True* the x-axis is inverted (conventional for T_eff).
    cmap : str
        Matplotlib colormap name used to color curves when plotting
        multiple isochrones and no explicit ``color`` is given in
        *kwargs*.  Ignored for a single isochrone.
    **kwargs
        Forwarded to :func:`matplotlib.pyplot.plot`.

    Returns
    -------
    fig, ax : Figure, Axes
    """
    fig, ax = _get_fig_ax(fig, ax)

    if isinstance(iso, Isochrone):
        isos: Sequence[Isochrone] = [iso]
    else:
        isos = iso

    colors = plt.get_cmap(cmap)(np.linspace(0.15, 0.85, len(isos)))

    for i, single in enumerate(isos):
        kw = dict(kwargs)
        kw.setdefault("lw", 1)
        if len(isos) > 1:
            kw.setdefault("color", colors[i])
        if iso_labels is not None:
            kw["label"] = iso_labels[i]

        xvals = _resolve_values(single, x)
        yvals = _resolve_values(single, y)
        ax.plot(xvals, yvals, **kw)

    ax.set_xlabel(_label(x))
    ax.set_ylabel(_label(y))

    if invert_x and not ax.xaxis_inverted():
        ax.invert_xaxis()

    if iso_labels is not None:
        ax.legend(fontsize="small")

    return fig, ax


def plot_color_magnitude(
    iso: Isochrone,
    band1: str,
    band2: str,
    mag: str | None = None,
    fig: Figure | None = None,
    ax: Axes | None = None,
    invert_y: bool = True,
    **kwargs,
) -> tuple[Figure, Axes]:
    """Plot a color–magnitude diagram.

    Uses :meth:`Photometry.get_color` to compute the color
    ``band1 − band2`` and plots it against a magnitude.

    Parameters
    ----------
    iso : Isochrone
        Isochrone with photometry.
    band1, band2 : str
        Band names passed to :meth:`Photometry.get_color`.
    mag : str, optional
        Band name for the y-axis magnitude.  Defaults to *band1*.
    fig : matplotlib Figure, optional
        Existing figure to draw on.  A new axes is added to it when *ax*
        is ``None``.  Ignored if *ax* is provided.
    ax : matplotlib Axes, optional
        Existing axes to draw on.  Takes priority over *fig*.  A new
        figure is created if both are ``None``.
    invert_y : bool
        If *True* the y-axis is inverted (brighter up).
    **kwargs
        Forwarded to :func:`matplotlib.pyplot.plot`.

    Returns
    -------
    fig, ax : Figure, Axes
    """
    fig, ax = _get_fig_ax(fig, ax)

    color = iso.photometry.get_color(band1, band2)
    if mag is None:
        mag = band1
    mag_tbl, mag_col = iso.photometry._resolve_column(mag)
    mag_vals = mag_tbl[mag_col]

    color_arr = _to_array(color)
    mag_arr = _to_array(mag_vals)

    kwargs.setdefault("lw", 1)
    ax.plot(color_arr, mag_arr, **kwargs)

    ax.set_xlabel(f"{_short(band1)} − {_short(band2)}")
    ax.set_ylabel(_short(mag))

    if invert_y and not ax.yaxis_inverted():
        ax.invert_yaxis()

    return fig, ax



def _get_fig_ax(
    fig: Figure | None = None,
    ax: Axes | None = None,
) -> tuple[Figure, Axes]:
    """Return *(fig, ax)*.

    Priority: *ax* > *fig* > create new figure.

    * If *ax* is given, return ``(ax.figure, ax)``.
    * If only *fig* is given, add a new subplot to it.
    * If neither is given, create a new figure with a single axes.
    """
    if ax is not None:
        return ax.figure, ax
    if fig is not None:
        return fig, fig.add_subplot()
    return plt.subplots()

def _to_array(val) -> np.ndarray:
    """Strip Quantity wrapper if present."""
    if isinstance(val, u.Quantity):
        return val.value
    return np.asarray(val)

def _resolve_values(iso: Isochrone, name: str) -> np.ndarray:
    """Get a numeric array for *name* from *iso*."""
    # try as a property
    try:
        val = getattr(iso, name)
        return _to_array(val)
    except (AttributeError, KeyError):
        pass
    # try as a data column
    if name in iso.data.colnames:
        return _to_array(iso.data[name])
    # try photometry (searches all system tables)
    try:
        tbl, col = iso.photometry._resolve_column(name)
        return _to_array(tbl[col])
    except (KeyError, ValueError):
        pass
    raise ValueError(f"Cannot resolve '{name}' on {iso!r}")

_LATEX: dict[str, str] = {
    "log_Teff": r"$\log\,T_{\rm eff}$ [K]",
    "log_L": r"$\log\,L\ [L_\odot]$",
    "log_g": r"$\log\,g$ [cm s$^{-2}$]",
    "mass": r"$M\ [M_\odot]$",
    "log_age": r"$\log\,\mathrm{age\ [yr]}$",
}

def _label(name: str) -> str:
    """Return a LaTeX axis label for *name*, falling back to *name* itself."""
    return _LATEX.get(name, name)

def _short(band: str) -> str:
    """Strip system prefix for axis labels, e.g. 'UBVRIplus: Bmag' → 'Bmag'."""
    if ": " in band:
        return band.split(": ", 1)[1]
    return band
