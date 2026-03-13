"""Get the MIST server paramter configuration.

Scrapes the MIST isochrone interpolation webform at
https://mist.science/interp_isos.html to keep option lists and default
values current.

.. note::

   Several form fields on the MIST website are injected by JavaScript
   after the page loads and therefore cannot be scraped from the static
   HTML source.  These fields are maintained as static
   definitions in ``_JS_INJECTED_*`` constants below.  They should be
   updated manually whenever the MIST website changes these options.
"""
import json
import os
import re

import requests
from bs4 import BeautifulSoup, NavigableString, Tag
from bs4.element import ResultSet

# default config
_FALLBACK_DEFAULTS: dict[str, str] = {
    "v_div_vcrit": "vvcrit0.4",
    "FeH_value": "0.00",
    "alpha_value": "p0",
    "age_value": "",
    "age_range_low": "5",
    "age_range_high": "10.3",
    "age_range_delta": "0.05",
    "Av_value": "0",
    "output_option": "theory",
    "output": "UBVRIplus",
}


# static definitions for JS-injected form fields (they're not present in the static HTML
# served by the website; they're created dynamically by JavaScript)
_JS_INJECTED_ROTATION: dict[str, list] = {
    "v_div_vcrit": [
        ("v/vcrit = 0.0", "vvcrit0.0"),
        ("v/vcrit = 0.4", "vvcrit0.4"),
    ],
}

_JS_INJECTED_COMPOSITION: dict[str, list] = {
    "FeH_value": [
        ("[Fe/H]", "0.00"),
    ],
    "alpha_value": [
        ("[α/Fe] = -0.2", "m2"),
        ("[α/Fe] = +0.0", "p0"),
        ("[α/Fe] = +0.2", "p2"),
        ("[α/Fe] = +0.4", "p4"),
        ("[α/Fe] = +0.6", "p6"),
    ],
}

_JS_INJECTED_AGE_TEXT: dict[str, list] = {
    "age_value": [
        ("", ""),
    ],
    "age_range_low": [
        ("", "5"),
    ],
    "age_range_high": [
        ("", "10.3"),
    ],
    "age_range_delta": [
        ("", "0.05"),
    ],
}

_JS_INJECTED_OUTPUT: dict[str, list] = {
    "output_option": [
        ("Theoretical", "theory"),
        ("Synthetic Photometry", "photometry"),
    ],
    "Av_value": [
        ("Extinction Av (0 ≤ Av ≤ 6)", "0"),
    ],
}

configuration: dict = {
    "url": "http://mist.science/interp_isos.html",
    "request_url": "http://mist.science/iso_form.php",
    "download_url": "http://mist.science/output",
    "query_options": [
        "version",
        "v_div_vcrit",
        "FeH_value",
        "alpha_value",
        "age_type",
        "age_scale",
        "age_value",
        "age_range_low",
        "age_range_high",
        "age_range_delta",
        "output_option",
        "output",
        "Av_value",
    ],
    "defaults": {},
}



def _clean(text: str) -> str:
    """Collapse whitespace and strip."""
    return re.sub(r'\s+', ' ', text).strip()


def _label_for_input(inp: Tag) -> str:
    """Return the label text for an <input> element.

    In order:
    1. If the input is wrapped in a <label>, use the label's direct text
       (excluding the input element itself).
    2. Look for a <label> element whose ``for`` attribute matches the
       input's ``id``.
    3. Check the immediate previous sibling(s) for text.
    4. Check the immediate next sibling for text.
    5. Return empty string.
    """
    # 1. check if wrapped in a <label>
    parent = inp.parent
    if parent and parent.name == "label":
        parts = []
        for child in parent.children:
            if child is inp:
                continue
            if isinstance(child, NavigableString):
                parts.append(str(child))
            elif isinstance(child, Tag) and child.name not in ("input", "select"):
                parts.append(child.get_text(separator=""))
        text = _clean("".join(parts))
        if text:
            return text

    # 2. look for a <label for="..."> matching the input's id
    inp_id = inp.get("id")
    if inp_id:
        form = inp.find_parent("form")
        if form:
            label_tag = form.find("label", attrs={"for": inp_id})
            if label_tag:
                text = _clean(label_tag.get_text(separator=" "))
                if text:
                    return text

    # 3. check preceding siblings
    prev = inp.previous_sibling
    attempts = 0
    while prev is not None and attempts < 5:
        if isinstance(prev, NavigableString):
            text = _clean(str(prev))
            if text:
                return text
        elif isinstance(prev, Tag):
            if prev.name in ("br",):
                prev = prev.previous_sibling
                attempts += 1
                continue
            text = _clean(prev.get_text(separator=" "))
            if text:
                return text
        prev = prev.previous_sibling if prev else None
        attempts += 1

    # 4. check following siblings
    nxt = inp.next_sibling
    if isinstance(nxt, NavigableString):
        text = _clean(str(nxt))
        if text:
            return text
    if isinstance(nxt, Tag) and nxt.name not in ("input", "select", "br"):
        text = _clean(nxt.get_text(separator=""))
        if text:
            return text

    return ""


def _parse_mist_radios(
    forms: BeautifulSoup | ResultSet,
    name: str,
) -> tuple[dict, dict]:
    """Parse radio buttons with the given name from MIST forms."""
    comps: dict = {}
    defaults: dict = {}
    for form in forms:
        items = []
        default_val = None
        found = form.find_all("input", {"name": name, "type": "radio"})
        if not found:
            found = [
                el for el in form.find_all("input", {"name": name})
                if el.get("type", "").lower() in ("radio", "")
                and el.get("value", "") != ""
            ]
        for inp in found:
            value = inp.get("value", "")
            label = _label_for_input(inp)
            if not label:
                label = value
            items.append((label, value))
            if inp.get("checked") is not None:
                default_val = value
        if items:
            comps[name] = items
            if default_val is not None:
                defaults[name] = default_val
            else:
                defaults[name] = items[0][1]
    return comps, defaults


def _parse_mist_text(
    forms: BeautifulSoup | ResultSet,
    name: str,
) -> tuple[dict, dict]:
    """Parse a text <input> with the given name."""
    comps: dict = {}
    defaults: dict = {}
    for form in forms:
        found = [
            el for el in form.find_all("input", {"name": name})
            if el.get("type", "text").lower()
            not in ("radio", "hidden", "submit", "checkbox")
        ]
        for inp in found:
            value = inp.get("value", "")
            label = _label_for_input(inp)
            comps[name] = [(label, value)]
            defaults[name] = value
    return comps, defaults


def _parse_mist_select(
    forms: BeautifulSoup | ResultSet,
    name: str,
) -> tuple[dict, dict]:
    """Parse a <select> element with the given name."""
    comps: dict = {}
    defaults: dict = {}
    for form in forms:
        for select in form.find_all("select", {"name": name}):
            items = []
            default_val = None
            for option in select.find_all("option"):
                value = option.get("value", "")
                if option.string is not None:
                    label = _clean(option.string)
                else:
                    parts = [
                        str(c) for c in option.children
                        if isinstance(c, NavigableString)
                    ]
                    label = _clean("".join(parts))
                items.append((label, value))
                if option.get("selected") is not None:
                    default_val = value
            if items:
                comps[name] = items
                if default_val is not None:
                    defaults[name] = default_val
                else:
                    defaults[name] = items[0][1]
    return comps, defaults


# webform section parsers
def _parse_hidden_inputs(
    forms: BeautifulSoup | ResultSet,
) -> tuple[dict, dict]:
    """Extract hidden input fields."""
    comps: dict = {}
    defaults: dict = {}
    for form in forms:
        for element in form.find_all("input", type="hidden"):
            name = element.get("name")
            value = element.get("value", "")
            if name:
                comps[name] = [(value, value)]
                defaults[name] = value
    return comps, defaults


def _get_version_info(
    forms: BeautifulSoup | ResultSet,
) -> tuple[dict, dict]:
    """Parse the MIST version <select>."""
    return _parse_mist_select(forms, "version")


def _get_rotation_info(
    forms: BeautifulSoup | ResultSet,
) -> tuple[dict, dict]:
    """Parse the *v/v_crit* radio buttons.

    These are injected by JavaScript on the MIST page, so attempt
    to scrape them but fall back to the static definitions.
    """
    comps, defaults = _parse_mist_radios(forms, "v_div_vcrit")
    if not comps:
        comps = dict(_JS_INJECTED_ROTATION)
        defaults = {"v_div_vcrit": _FALLBACK_DEFAULTS["v_div_vcrit"]}
    return comps, defaults


def _get_composition_info(
    forms: BeautifulSoup | ResultSet,
) -> tuple[dict, dict]:
    """Parse the 'Composition' section: [Fe/H] text input and [α/Fe] radio button.

    These are injected by JavaScript on the MIST page, so attempt
    to scrape them but fall back to the static definitions.
    """
    comps: dict = {}
    defaults: dict = {}

    # [Fe/H] text input
    new_comps, new_defaults = _parse_mist_text(forms, "FeH_value")
    if not new_comps:
        new_comps = {"FeH_value": _JS_INJECTED_COMPOSITION["FeH_value"]}
        new_defaults = {"FeH_value": _FALLBACK_DEFAULTS["FeH_value"]}
    comps.update(new_comps)
    defaults.update(new_defaults)

    # [alpha/Fe] select element
    new_comps, new_defaults = _parse_mist_select(forms, "alpha_value")
    if not new_comps:
        new_comps = {"alpha_value": _JS_INJECTED_COMPOSITION["alpha_value"]}
        new_defaults = {"alpha_value": _FALLBACK_DEFAULTS["alpha_value"]}
    comps.update(new_comps)
    defaults.update(new_defaults)

    return comps, defaults


def _get_age_type_info(
    forms: BeautifulSoup | ResultSet,
) -> tuple[dict, dict]:
    """Parse the age-type radio buttons and associated text fields.

    The text fields (age_value, age_range_low, etc.) are injected by
    JavaScript, so fall back to static definitions if not found.
    """
    comps, defaults = _parse_mist_radios(forms, "age_type")

    # age_scale radio buttons
    new_comps, new_defaults = _parse_mist_radios(forms, "age_scale")
    comps.update(new_comps)
    defaults.update(new_defaults)

    # associated text fields — JS-injected, with fallbacks
    for name in ("age_value", "age_range_low", "age_range_high",
                 "age_range_delta"):
        new_comps, new_defaults = _parse_mist_text(forms, name)
        if not new_comps and name in _JS_INJECTED_AGE_TEXT:
            new_comps = {name: _JS_INJECTED_AGE_TEXT[name]}
            new_defaults = {name: _FALLBACK_DEFAULTS.get(name, "")}
        comps.update(new_comps)
        defaults.update(new_defaults)

    return comps, defaults


def _get_output_info(
    forms: BeautifulSoup | ResultSet,
) -> tuple[dict, dict]:
    """Parse output options: radio buttons, photometric system select, extinction.

    Av_value is injected by JavaScript, so fall
    back to static definitions if not found.
    """
    comps: dict = {}
    defaults: dict = {}

    # output_option: theory vs. photometry radio
    new_comps, new_defaults = _parse_mist_radios(forms, "output_option")
    if "output_option" in new_comps:
        cleaned = []
        for label, value in new_comps["output_option"]:
            if value == "photometry":
                cleaned.append(("Synthetic Photometry", value))
            elif value == "theory":
                cleaned.append(("Theoretical", value))
            else:
                cleaned.append((_clean(label), value))
        new_comps["output_option"] = cleaned
    comps.update(new_comps)
    defaults.update(new_defaults)

    # output: photometric system <select>
    new_comps, new_defaults = _parse_mist_select(forms, "output")
    comps.update(new_comps)
    defaults.update(new_defaults)

    # Av_value text input — JS-injected
    new_comps, new_defaults = _parse_mist_text(forms, "Av_value")
    if not new_comps:
        new_comps = {"Av_value": _JS_INJECTED_OUTPUT["Av_value"]}
        new_defaults = {"Av_value": _FALLBACK_DEFAULTS["Av_value"]}
    comps.update(new_comps)
    defaults.update(new_defaults)

    return comps, defaults


def _apply_js_fallbacks():
    """Ensure JS-injected sections are present in ``configuration``.

    Called after fresh scrapes and cache loads, because the
    cached JSON may have been written before the JS fallbacks were
    added, or the scrape may not have found these elements in the
    static HTML.
    """
    # rotation
    if not configuration.get("rotation"):
        configuration["rotation"] = {
            k: list(v) for k, v in _JS_INJECTED_ROTATION.items()
        }
    # composition
    comp = configuration.setdefault("composition", {})
    if "FeH_value" not in comp:
        comp["FeH_value"] = list(_JS_INJECTED_COMPOSITION["FeH_value"])
    if "alpha_value" not in comp:
        comp["alpha_value"] = list(_JS_INJECTED_COMPOSITION["alpha_value"])
    # age text fields
    age = configuration.setdefault("age", {})
    for name, fallback in _JS_INJECTED_AGE_TEXT.items():
        if name not in age:
            age[name] = list(fallback)
    # Av_value under output
    output = configuration.setdefault("output", {})
    for name, fallback in _JS_INJECTED_OUTPUT.items():
        if name not in output:
            output[name] = list(fallback)
    # ensure all fallback defaults are present
    defs = configuration.setdefault("defaults", {})
    for k, v in _FALLBACK_DEFAULTS.items():
        if k not in defs or defs[k] in (None, ""):
            defs[k] = v


def _get_page_info():
    """Scrape the MIST webform and rebuild ``configuration`` in place.

    Fields that exist only in the static HTML are scraped directly.
    Fields that are injected by JavaScript fall back to the static
    definitions in the ``_JS_INJECTED_*`` constants.
    """
    response = requests.get(configuration["url"], timeout=30)
    response.raise_for_status()

    soup = BeautifulSoup(response.text, "html.parser")
    forms = soup.find_all("form")

    scraped_defaults: dict[str, str] = dict(_FALLBACK_DEFAULTS)

    sections = [
        ("hidden", _parse_hidden_inputs(forms)),
        ("version", _get_version_info(forms)),
        ("rotation", _get_rotation_info(forms)),
        ("composition", _get_composition_info(forms)),
        ("age", _get_age_type_info(forms)),
        ("output", _get_output_info(forms)),
    ]

    for key, (comps, defaults) in sections:
        configuration[key] = comps
        for k, v in defaults.items():
            if v is not None:
                scraped_defaults[k] = v

    configuration["defaults"] = scraped_defaults

    # fill in anything the static HTML couldn't provide
    _apply_js_fallbacks()


def _write_files():
    """Persist configuration as JSON."""
    base_directory = os.path.dirname(os.path.abspath(__file__))
    config_file = os.path.join(base_directory, "mist_config.json")

    with open(config_file, "w") as f:
        json.dump(configuration, f, indent=4)


def reload_config():
    """Load (or create) the local JSON configuration cache."""
    base_directory = os.path.dirname(os.path.abspath(__file__))
    config_file = os.path.join(base_directory, "mist_config.json")

    if os.path.isfile(config_file):
        with open(config_file) as f:
            loaded = json.load(f)
        if loaded.get("defaults"):
            configuration.update(loaded)
            # ensure query_options is always present and complete
            _canonical_query_options = [
                "version",
                "v_div_vcrit",
                "FeH_value",
                "alpha_value",
                "age_type",
                "age_scale",
                "age_value",
                "age_range_low",
                "age_range_high",
                "age_range_delta",
                "output_option",
                "output",
                "Av_value",
            ]
            if configuration.get("query_options") != _canonical_query_options:
                configuration["query_options"] = _canonical_query_options
            # apply JS fallbacks and re-persist if anything was added
            before = json.dumps(configuration, sort_keys=True)
            _apply_js_fallbacks()
            after = json.dumps(configuration, sort_keys=True)
            if before != after:
                _write_files()
        else:
            update_config()
    else:
        update_config()


def update_config():
    """Scrape the MIST website, refresh the configuration, and save it."""
    _get_page_info()
    _write_files()


# auto-load on import
reload_config()
