# EZMIST configuration file

_This file contains the configuration for the EZMIST package. It is generated automatically by the package and should not be modified manually._

All detailed description of the parameters can be found on the [MIST webpage](https://mist.science/interp_isos.html).

## MIST Version `version`

| value | description |
| --- | --- |
| MIST1 | 1.2 |
| MIST2 | 2.5 |

## Rotation `v_div_vcrit`

| value | description |
| --- | --- |
| vvcrit0.0 | v/vcrit = 0.0 |
| vvcrit0.4 | v/vcrit = 0.4 |

## Composition

### `FeH_value`

| parameter | value | description |
| --- | --- | --- |
| `FeH_value` | 0 | [Fe/H] = |

### `afe` ([α/Fe])

| value | description |
| --- | --- |
| afep0.0 | [α/Fe] = +0.0 (solar-scaled) |
| afep0.2 | [α/Fe] = +0.2 |
| afep0.4 | [α/Fe] = +0.4 |
| afep0.6 | [α/Fe] = +0.6 |

## Age options

### `age_type`

| value | description |
| --- | --- |
| single | Age unit is years; available range is 5 ≤ log(Age[yr]) ≤ 10.3 |
| range | Single age |
| list | in steps of |
| standard | (space separated) |

### `age_scale`

| value | description |
| --- | --- |
| linear | Age |
| log10 | Linear Scale |

### Age parameters

| parameter | value | description |
| --- | --- | --- |
| `age_value` |  | Single age |
| `age_range_low` |  | Range of ages from |
| `age_range_high` |  | to |
| `age_range_delta` |  | in steps of |

## Output options

### `output_option`

| value | description |
| --- | --- |
| theory | Theoretical |
| photometry | Synthetic Photometry |

### Photometric systems `output`

| value | description |
| --- | --- |
| CFHTugriz | CFHT/MegaCam |
| DECam | DECam |
| HST_ACS_HRC | HST ACS/HRC |
| HST_ACS_SBC | HST ACS/SBC |
| HST_ACS_WFC | HST ACS/WFC |
| HST_WFC3 | HST WFC3/UVIS+IR |
| HST_WFPC2 | HST WFPC2 |
| IPHAS | INT / IPHAS |
| GALEX | GALEX |
| JWST | JWST NIRCAM |
| NIRISS | JWST NIRISS |
| PanSTARRS | PanSTARRS |
| Roman | Roman (formerly WFIRST) |
| LSST | Rubin / LSST |
| SDSSugriz | SDSS |
| SkyMapper | SkyMapper |
| SPITZER | Spitzer IRAC |
| SPLUS | S-PLUS |
| HSC | Subaru Hyper Suprime-Cam |
| Swift | Swift |
| UBVRIplus | UBV(RI)c + 2MASS + Kepler + Hipparcos + Gaia + Tess |
| UKIDSS | UKIDSS |
| UVIT | UVIT |
| VISTA | VISTA |
| WashDDOuvby | Washington + Strömgren + DDO51 |
| WISE | WISE |

### Extinction

| parameter | value | description |
| --- | --- | --- |
| `Av_value` | 0 | Extinction Av = |

## Default values

| parameter | value |
| --- | --- |
| `v_div_vcrit` | vvcrit0.4 |
| `FeH_value` | 0 |
| `afe` | afep0.0 |
| `age_value` |  |
| `age_range_low` |  |
| `age_range_high` |  |
| `age_range_delta` |  |
| `Av_value` | 0 |
| `version` | MIST2 |
| `age_type` | standard |
| `age_scale` | log10 |
| `output_option` | theory |
| `output` | UBVRIplus |
