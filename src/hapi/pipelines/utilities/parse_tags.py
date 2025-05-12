import re

from hapi_schema.utils.enums import Gender
from hdx.utilities.matching import multiple_replace
from hxl.model import Column, TagPattern


def get_gender_and_age_range(hxl_tag: str) -> (str, str):
    gender = "all"
    age_range = "all"
    col = Column.parse(hxl_tag)
    gender_patterns = {
        TagPattern.parse(f"#*+{gender.value}"): gender.value for gender in Gender
    }
    for pattern in gender_patterns:
        if pattern.match(col):
            gender = gender_patterns[pattern]

    age_component = [
        c for c in hxl_tag.split("+") if c.startswith("age") or c.endswith("age")
    ]
    if len(age_component) == 0:
        return gender, age_range
    age_component = multiple_replace(
        age_component[0], {"age_": "", "age": "", "_age": ""}
    )
    # Check if age component contains any numbers
    if re.search(r"\d", age_component):
        if age_component.endswith("plus"):
            age_range = multiple_replace(age_component, {"plus": "+", "_plus": "+"})
        else:
            age_range = age_component.replace("_", "-")

    return gender, age_range


def get_min_and_max_age(age_range: str) -> (int | None, int | None):
    if age_range == "all" or age_range == "unknown":
        return None, None
    ages = age_range.split("-")
    if len(ages) == 2:
        # Format: 0-5
        min_age, max_age = int(ages[0]), int(ages[1])
    else:
        # Format: 80+
        min_age = int(age_range.replace("+", ""))
        max_age = None
    return min_age, max_age
