from typing import Dict, List, Optional


def get_provider_name(
    values: Dict | List,
    header_or_hxl_tag: str,
    headers_or_hxl_tags: Optional[List[str]] = None,
    admin_code: Optional[str] = None,
    i: Optional[int] = None,
) -> str:
    if headers_or_hxl_tags is None:
        provider_name = values.get(header_or_hxl_tag, "")
        if provider_name is None:
            provider_name = ""
        return provider_name
    if header_or_hxl_tag not in headers_or_hxl_tags:
        return ""
    provider_name = values[headers_or_hxl_tags.index(header_or_hxl_tag)]
    if admin_code is not None:
        provider_name = provider_name[admin_code]
    if i is not None:
        provider_name = provider_name[i]
    if provider_name is None:
        provider_name = ""
    return provider_name
