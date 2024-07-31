from typing import Dict, List

from hdx.location.phonetics import Phonetics
from hdx.utilities.text import normalise

MATCH_THRESHOLD = 5


def get_code_from_name(
    name: str,
    code_lookup: Dict[str, str],
    unmatched: List[str],
    fuzzy_match: bool = True,
) -> str | None:
    """
    Given a name (org type, sector, etc), return the corresponding code.

    Args:
        name (str): Name to match
        code_lookup (dict): Dictionary of official names and codes
        unmatched (List[str]): List of unmatched names
        fuzzy_match (bool): Allow fuzzy matching or not

    Returns:
        str or None: Matching code
    """
    code = code_lookup.get(name)
    if code:
        return code
    if name in unmatched:
        return None
    name_clean = normalise(name)
    code = code_lookup.get(name_clean)
    if code:
        code_lookup[name] = code
        return code
    if len(name) <= MATCH_THRESHOLD:
        unmatched.append(name)
        return None
    if not fuzzy_match:
        unmatched.append(name)
        return None
    names = [x for x in code_lookup.keys() if len(x) > MATCH_THRESHOLD]
    name_index = Phonetics().match(
        possible_names=names,
        name=name,
        alternative_name=name_clean,
    )
    if name_index is None:
        unmatched.append(name)
        return None
    code = code_lookup.get(names[name_index])
    if code:
        code_lookup[name] = code
        code_lookup[name_clean] = code
    return code
