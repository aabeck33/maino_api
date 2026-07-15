from __future__ import annotations

from typing import Any, Iterable, Optional, Tuple

# These ranges are approximate Brazilian CEP groups used to infer state (UF) from postal code.
# They rely on the first three digits of the CEP and are intended for native, offline mapping.
BRAZIL_CEP_UF_RANGES = [
    (1, 199, "SP"),
    (200, 289, "RJ"),
    (290, 299, "ES"),
    (300, 399, "MG"),
    (400, 489, "BA"),
    (490, 499, "SE"),
    (500, 569, "PE"),
    (570, 579, "AL"),
    (580, 589, "PB"),
    (590, 599, "RN"),
    (600, 639, "CE"),
    (640, 649, "PI"),
    (650, 659, "MA"),
    (660, 688, "PA"),
    (689, 689, "AP"),
    (690, 692, "AM"),
    (693, 693, "RR"),
    (694, 698, "AM"),
    (699, 699, "AC"),
    (700, 736, "DF"),
    (737, 767, "GO"),
    (768, 769, "RO"),
    (770, 779, "TO"),
    (780, 788, "MT"),
    (790, 799, "MS"),
    (800, 879, "PR"),
    (880, 899, "SC"),
    (900, 999, "RS"),
]

BRAZIL_STATE_CENTROIDS = {
    "AC": (-8.77, -70.55),
    "AL": (-9.62, -36.82),
    "AM": (-3.47, -65.10),
    "AP": (1.41, -52.52),
    "BA": (-12.96, -38.51),
    "CE": (-5.20, -39.53),
    "DF": (-15.79, -47.86),
    "ES": (-19.19, -40.34),
    "GO": (-16.64, -49.31),
    "MA": (-2.55, -44.30),
    "MG": (-18.10, -44.38),
    "MS": (-20.51, -54.54),
    "MT": (-12.64, -55.42),
    "PA": (-5.53, -52.30),
    "PB": (-7.06, -35.55),
    "PE": (-8.28, -35.07),
    "PI": (-7.53, -42.77),
    "PR": (-24.89, -51.55),
    "RJ": (-22.91, -43.17),
    "RN": (-5.22, -36.52),
    "RO": (-11.22, -62.80),
    "RR": (2.82, -60.67),
    "RS": (-30.03, -51.22),
    "SC": (-27.33, -49.44),
    "SE": (-10.90, -37.07),
    "TO": (-10.25, -48.30),
}


def extract_digits(value: Any) -> str:
    if value is None:
        return ""
    raw = str(value)
    return "".join(char for char in raw if char.isdigit())


def normalize_cep(raw: Any) -> str:
    cep_digits = extract_digits(raw)
    if len(cep_digits) >= 8:
        return f"{cep_digits[:5]}-{cep_digits[5:8]}"
    return raw.strip() if isinstance(raw, str) else str(raw)


def map_cep_to_uf(cep: str) -> str:
    cep_digits = extract_digits(cep)
    if len(cep_digits) < 2:
        return "N/A"

    # Using the first three digits when available to increase accuracy for border ranges.
    prefix = int(cep_digits[:3]) if len(cep_digits) >= 3 else int(cep_digits[:2])
    for start, end, uf in BRAZIL_CEP_UF_RANGES:
        if start <= prefix <= end:
            return uf
    return "N/A"


def safe_float(value: Any) -> float:
    if value is None:
        return 0.0
    if isinstance(value, (int, float)):
        return float(value)

    value_str = str(value).strip()
    if not value_str:
        return 0.0

    # Preserve dot decimal separator when present, while still supporting
    # Brazilian-style values like "1.234,56".
    if "." in value_str and "," in value_str:
        normalized = value_str.replace(".", "").replace(",", ".")
    elif "," in value_str:
        normalized = value_str.replace(",", ".")
    else:
        normalized = value_str

    try:
        return float(normalized)
    except ValueError:
        return 0.0


def find_value_by_keys(obj: Any, keys: Iterable[str]) -> Optional[Any]:
    if obj is None:
        return None

    key_set = {key.lower() for key in keys}

    if isinstance(obj, dict):
        for key, value in obj.items():
            if key.lower() in key_set:
                return value
        for value in obj.values():
            found = find_value_by_keys(value, keys)
            if found is not None:
                return found
    elif isinstance(obj, list):
        for item in obj:
            found = find_value_by_keys(item, keys)
            if found is not None:
                return found

    return None
