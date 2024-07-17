from typing import Dict

from hdx.location.phonetics import Phonetics
from hdx.utilities.text import normalise

MATCH_THRESHOLD = 5


def get_code_from_name(
    name: str,
    code_lookup: Dict[str, str],
    fuzzy_match: bool = False,
) -> str | None:
    """
    Given a name (org type, sector, etc), return the corresponding code.

    Args:
        name (str): Name to match
        code_lookup (dict): Dictionary of official names and codes
        fuzzy_match (bool): Allow fuzzy matching or not

    Returns:
        str or None: matching code
    """
    code = code_lookup.get(name)
    if code:
        return code
    name_clean = normalise(name)
    code = code_lookup.get(name_clean)
    if code:
        return code
    if len(name) <= MATCH_THRESHOLD:
        return None
    if not fuzzy_match:
        return None
    names = list(code_lookup.keys())
    name_index = Phonetics().match(
        possible_names=names,
        name=name,
        alternative_name=name_clean,
    )
    if name_index is None:
        return None
    name = names[name_index]
    code = code_lookup.get(name)
    if code:
        code_lookup[name_clean] = code
    return code
