from typing import Dict, List


def add_defaults(config: Dict) -> Dict:
    default_list = _find_defaults(config)
    for default_key in default_list:
        default = config[default_key]
        matching_top_level_keys = _find_matching_top_level_keys(
            config, default_key
        )
        for top_level_key in matching_top_level_keys:
            config = _scraper_add_defaults(config, default, top_level_key)

        del config[default_key]
    return config


def _find_defaults(config: Dict) -> List:
    default_list = []
    for key in config:
        key_components = key.rsplit("_", 1)
        if len(key_components) == 2 and key_components[1] == "default":
            default_list.append(key)
    return default_list


def _find_matching_top_level_keys(config: Dict, default_key: str) -> List[str]:
    matching_top_level_keys = []
    default_prefix = default_key.rsplit("_", 1)[0]
    for top_level_key in config:
        top_level_key_prefix = top_level_key.rsplit("_", 1)[0]
        if (
            top_level_key != default_key
            and top_level_key_prefix == default_prefix
        ):
            matching_top_level_keys.append(top_level_key)
    return matching_top_level_keys


def _scraper_add_defaults(
    config: Dict, default: Dict, top_level_key: str
) -> Dict:
    for scraper in default["scrapers_with_defaults"]:
        if scraper in config[top_level_key]:
            scraper_config = config[top_level_key][scraper]
            scraper_config = _combine_default(scraper_config, default)
            config[top_level_key][scraper] = scraper_config
    return config


def _combine_default(country: Dict, default: Dict) -> Dict:
    for list_name in ("input", "list", "output", "output_hxl"):
        if list_name not in country.keys():
            country[list_name] = []
        if list_name in default:
            country[list_name] = country[list_name] + default[list_name]
    for other_parameter in (
        "format",
        "xlsx2csv",
        "sheet",
        "headers",
        "use_hxl",
        "admin",
        "admin_exact",
        "filter_cols",
        "prefilter",
    ):
        if (
            other_parameter in default
            and other_parameter not in country.keys()
        ):
            country[other_parameter] = default[other_parameter]
    return country
