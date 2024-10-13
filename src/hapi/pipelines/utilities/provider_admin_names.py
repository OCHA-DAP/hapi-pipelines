from typing import Dict, List, Optional


def get_provider_name(
    values: Dict | List,
    hxl_tag: str,
    hxl_tags: Optional[List[str]] = None,
    admin_code: Optional[str] = None,
    i: Optional[int] = None,
) -> str:
    if hxl_tags is None:
        provider_name = values.get(hxl_tag, "")
        if provider_name is None:
            provider_name = ""
        return provider_name
    if hxl_tag not in hxl_tags:
        return ""
    provider_name = values[hxl_tags.index(hxl_tag)]
    if admin_code is not None:
        provider_name = provider_name[admin_code]
    if i is not None:
        provider_name = provider_name[i]
    if provider_name is None:
        provider_name = ""
    return provider_name
