
import astropy.units as u

PADOVA_COLUMN_UNITS: dict[str, u.UnitBase] = {
    "Zini": u.dimensionless_unscaled,   # initial metal fraction
    "MH": u.dex,                        # [M/H]
    "logAge": u.dex(u.yr),              # log10(age/yr)
    "Mini": u.Msun,                     # initial mass
    "int_IMF": u.dimensionless_unscaled,# integral of the IMF
    "Mass": u.Msun,                     # current mass
    "logL": u.dex(u.Lsun),              # log10(L/Lsun)
    "logTe": u.dex(u.K),                # log10(Teff/K)
    "logg": u.dex(u.cm / u.s**2),       # log10(g / (cm/s^2))
    "label": u.dimensionless_unscaled,  # evolution stage label
    "McoreTP": u.Msun,                  # core mass at first thermal pulse
    "C_O": u.dimensionless_unscaled,    # surface C/O ratio
    "period0": u.day,                   # fundamental pulsation period
    "period1": u.day,                   # first overtone period
    "period2": u.day,                   # second overtone period
    "period3": u.day,                   # third overtone period
    "period4": u.day,                   # fourth overtone period
    "pmode": u.dimensionless_unscaled,  # dominant pulsation mode
    "Mloss": u.Msun / u.yr,             # mass-loss rate
    "tau1m": u.dimensionless_unscaled,  # optical depth at 1 micron
    "X": u.dimensionless_unscaled,      # hydrogen mass fraction
    "Y": u.dimensionless_unscaled,      # helium mass fraction
    "Xc": u.dimensionless_unscaled,     # central hydrogen mass fraction
    "Xn": u.dimensionless_unscaled,     # central nitrogen fraction
    "Xo": u.dimensionless_unscaled,     # central oxygen fraction
    "Cexcess": u.dimensionless_unscaled,# carbon excess
    "Z": u.dimensionless_unscaled,      # metal fraction
    "mbolmag": u.mag,                   # bolometric magnitude
    "evol": u.dimensionless_unscaled,   # continuous evolution phase
    "logLLp": u.dex(u.Lsun),            # log luminosity (alternative)
    "logTeLp": u.dex(u.K),              # log Teff (alternative)
    "loggLp": u.dex(u.cm / u.s**2),     # log g (alternative)
}

MIST_COLUMN_UNITS: dict[str, u.UnitBase] = {
    "EEP": u.dimensionless_unscaled,                # equivalent evolutionary point
    "log10_isochrone_age_yr": u.dex(u.yr),           # log10(age/yr)
    "phase": u.dimensionless_unscaled,               # evolution phase label
    "initial_mass": u.Msun,
    "star_mass": u.Msun,
    "star_mdot": u.Msun / u.yr,                      # mass-loss rate
    "he_core_mass": u.Msun,
    "c_core_mass": u.Msun,
    "o_core_mass": u.Msun,
    "mass_conv_core": u.Msun,
    "log_L": u.dex(u.Lsun),
    "log_L_div_Ledd": u.dex,
    "log_LH": u.dex(u.Lsun),
    "log_LHe": u.dex(u.Lsun),
    "log_LZ": u.dex(u.Lsun),
    "log_abs_Lgrav": u.dex(u.Lsun),
    "log_Teff": u.dex(u.K),
    "log_R": u.dex(u.Rsun),
    "log_g": u.dex(u.cm / u.s**2),
    "log_surf_cell_z": u.dex,
    # rotation
    "surf_avg_omega": u.rad / u.s,
    "surf_avg_v_rot": u.km / u.s,
    "surf_avg_omega_crit": u.rad / u.s,
    "surf_avg_omega_div_omega_crit": u.dimensionless_unscaled,
    "surf_avg_v_crit": u.km / u.s,
    "surf_avg_v_div_v_crit": u.dimensionless_unscaled,
    "surf_avg_Lrad_div_Ledd": u.dimensionless_unscaled,
    "v_div_csound_surf": u.dimensionless_unscaled,
    "surf_r_equatorial_div_r": u.dimensionless_unscaled,
    "surf_r_polar_div_r": u.dimensionless_unscaled,
    "total_angular_momentum": u.g * u.cm**2 / u.s,
    # darkening
    "grav_dark_L_polar": u.Lsun,
    "grav_dark_Teff_polar": u.K,
    "grav_dark_L_equatorial": u.Lsun,
    "grav_dark_Teff_equatorial": u.K,
    # surface abundances
    "surf_num_c12_div_num_o16": u.dimensionless_unscaled,
    "surface_h1": u.dimensionless_unscaled,
    "surface_h2": u.dimensionless_unscaled,
    "surface_he3": u.dimensionless_unscaled,
    "surface_he4": u.dimensionless_unscaled,
    "surface_li7": u.dimensionless_unscaled,
    "surface_be7": u.dimensionless_unscaled,
    "surface_be9": u.dimensionless_unscaled,
    "surface_be10": u.dimensionless_unscaled,
    "surface_b8": u.dimensionless_unscaled,
    "surface_c12": u.dimensionless_unscaled,
    "surface_c13": u.dimensionless_unscaled,
    "surface_n13": u.dimensionless_unscaled,
    "surface_n14": u.dimensionless_unscaled,
    "surface_n15": u.dimensionless_unscaled,
    "surface_o14": u.dimensionless_unscaled,
    "surface_o15": u.dimensionless_unscaled,
    "surface_o16": u.dimensionless_unscaled,
    "surface_o17": u.dimensionless_unscaled,
    "surface_o18": u.dimensionless_unscaled,
    "surface_f17": u.dimensionless_unscaled,
    "surface_f18": u.dimensionless_unscaled,
    "surface_f19": u.dimensionless_unscaled,
    "surface_ne18": u.dimensionless_unscaled,
    "surface_ne19": u.dimensionless_unscaled,
    "surface_ne20": u.dimensionless_unscaled,
    "surface_ne21": u.dimensionless_unscaled,
    "surface_ne22": u.dimensionless_unscaled,
    "surface_na21": u.dimensionless_unscaled,
    "surface_na22": u.dimensionless_unscaled,
    "surface_na23": u.dimensionless_unscaled,
    "surface_na24": u.dimensionless_unscaled,
    "surface_mg23": u.dimensionless_unscaled,
    "surface_mg24": u.dimensionless_unscaled,
    "surface_mg25": u.dimensionless_unscaled,
    "surface_mg26": u.dimensionless_unscaled,
    "surface_al25": u.dimensionless_unscaled,
    "surface_al26": u.dimensionless_unscaled,
    "surface_al27": u.dimensionless_unscaled,
    "surface_si27": u.dimensionless_unscaled,
    "surface_si28": u.dimensionless_unscaled,
    "surface_si29": u.dimensionless_unscaled,
    "surface_si30": u.dimensionless_unscaled,
    "surface_p30": u.dimensionless_unscaled,
    "surface_p31": u.dimensionless_unscaled,
    "surface_s31": u.dimensionless_unscaled,
    "surface_s32": u.dimensionless_unscaled,
    "surface_s33": u.dimensionless_unscaled,
    "surface_s34": u.dimensionless_unscaled,
    "surface_ca40": u.dimensionless_unscaled,
    "surface_ti48": u.dimensionless_unscaled,
    "surface_fe56": u.dimensionless_unscaled,
    # thermodynamics
    "log_center_T": u.dex(u.K),
    "log_center_Rho": u.dex(u.g / u.cm**3),
    "center_degeneracy": u.dimensionless_unscaled,
    "center_omega": u.rad / u.s,
    "center_gamma": u.dimensionless_unscaled,
    # abundances
    "center_h1": u.dimensionless_unscaled,
    "center_h2": u.dimensionless_unscaled,
    "center_he3": u.dimensionless_unscaled,
    "center_he4": u.dimensionless_unscaled,
    "center_li7": u.dimensionless_unscaled,
    "center_be7": u.dimensionless_unscaled,
    "center_be9": u.dimensionless_unscaled,
    "center_be10": u.dimensionless_unscaled,
    "center_b8": u.dimensionless_unscaled,
    "center_c12": u.dimensionless_unscaled,
    "center_c13": u.dimensionless_unscaled,
    "center_n13": u.dimensionless_unscaled,
    "center_n14": u.dimensionless_unscaled,
    "center_n15": u.dimensionless_unscaled,
    "center_o14": u.dimensionless_unscaled,
    "center_o15": u.dimensionless_unscaled,
    "center_o16": u.dimensionless_unscaled,
    "center_o17": u.dimensionless_unscaled,
    "center_o18": u.dimensionless_unscaled,
    "center_f17": u.dimensionless_unscaled,
    "center_f18": u.dimensionless_unscaled,
    "center_f19": u.dimensionless_unscaled,
    "center_ne18": u.dimensionless_unscaled,
    "center_ne19": u.dimensionless_unscaled,
    "center_ne20": u.dimensionless_unscaled,
    "center_ne21": u.dimensionless_unscaled,
    "center_ne22": u.dimensionless_unscaled,
    "center_na21": u.dimensionless_unscaled,
    "center_na22": u.dimensionless_unscaled,
    "center_na23": u.dimensionless_unscaled,
    "center_na24": u.dimensionless_unscaled,
    "center_mg23": u.dimensionless_unscaled,
    "center_mg24": u.dimensionless_unscaled,
    "center_mg25": u.dimensionless_unscaled,
    "center_mg26": u.dimensionless_unscaled,
    "center_al25": u.dimensionless_unscaled,
    "center_al26": u.dimensionless_unscaled,
    "center_al27": u.dimensionless_unscaled,
    "center_si27": u.dimensionless_unscaled,
    "center_si28": u.dimensionless_unscaled,
    "center_si29": u.dimensionless_unscaled,
    "center_si30": u.dimensionless_unscaled,
    "center_p30": u.dimensionless_unscaled,
    "center_p31": u.dimensionless_unscaled,
    "center_s31": u.dimensionless_unscaled,
    "center_s32": u.dimensionless_unscaled,
    "center_s33": u.dimensionless_unscaled,
    "center_s34": u.dimensionless_unscaled,
    "center_ca40": u.dimensionless_unscaled,
    "center_ti48": u.dimensionless_unscaled,
    "center_fe56": u.dimensionless_unscaled,
    # nuclear burning
    "pp": u.dex(u.Lsun),
    "cno": u.dex(u.Lsun),
    "tri_alfa": u.dex(u.Lsun),
    "burn_c": u.dex(u.Lsun),
    "burn_n": u.dex(u.Lsun),
    "burn_o": u.dex(u.Lsun),
    "c12_c12": u.dex(u.Lsun),
    # asteroseismology
    "apsidal_constant_k2": u.dimensionless_unscaled,
    "delta_nu": u.uHz,
    "delta_Pg": u.s,
    "nu_max": u.uHz,
    "acoustic_cutoff": u.uHz,
    # misc and convection
    "max_conv_vel_div_csound": u.dimensionless_unscaled,
    "max_gradT_div_grada": u.dimensionless_unscaled,
    "gradT_excess_alpha": u.dimensionless_unscaled,
    "min_Pgas_div_P": u.dimensionless_unscaled,
    "max_L_rad_div_Ledd": u.dimensionless_unscaled,
    "e_thermal": u.erg,
    "conv_env_top_mass": u.Msun,
    "conv_env_bot_mass": u.Msun,
    "conv_env_top_radius": u.Rsun,
    "conv_env_bot_radius": u.Rsun,
    "conv_env_turnover_time_l_t": u.s,
    "conv_env_turnover_time_l_b": u.s,
    "conv_env_turnover_time_g": u.s,
    "envelope_binding_energy": u.erg,
    "total_moment_of_inertia": u.g * u.cm**2,
}


def _get_column_units(database: str) -> dict[str, u.UnitBase]:
    """Return the column-units dict for the given database."""
    if database == "padova":
        return PADOVA_COLUMN_UNITS
    elif database == "mist":
        return MIST_COLUMN_UNITS
    raise ValueError(f"Unknown database {database!r}")


def _get_unit(colname: str, column_units: dict[str, u.UnitBase]) -> u.UnitBase:
    """Return the unit for a given column name.

    Known columns get their physical unit; photometric filter columns
    (names ending in ``"mag"``) get `~astropy.units.mag`; everything
    else is treated as dimensionless.
    """
    if colname in column_units:
        return column_units[colname]
    if colname.endswith("mag"):
        return u.mag
    return u.dimensionless_unscaled
