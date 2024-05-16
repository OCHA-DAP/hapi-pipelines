from hapi.pipelines.utilities.parse_tags import (
    get_gender_and_age_range,
    get_min_and_max_age,
)


def test_get_gender_and_age_range():
    assert get_gender_and_age_range("#population+m+total") == ("m", "*")
    assert get_gender_and_age_range("#population+age_20_24+total") == (
        "*",
        "20-24",
    )
    assert get_gender_and_age_range("#population+f+age_65_plus") == (
        "f",
        "65+",
    )
    assert get_gender_and_age_range("#inneed+age0_17") == ("*", "0-17")
    assert get_gender_and_age_range("#targeted+edu+m+age18plus") == (
        "m",
        "18+",
    )
    assert get_gender_and_age_range("#affected+m+unknown_age") == (
        "m",
        "unknown",
    )
    assert get_gender_and_age_range("#affected+f+adolescents+age_12_17") == (
        "f",
        "12-17",
    )


def test_get_min_and_max_age():
    assert get_min_and_max_age("*") == (None, None)
    assert get_min_and_max_age("20-24") == (20, 24)
    assert get_min_and_max_age("65+") == (65, None)
    assert get_min_and_max_age("unknown") == (None, None)
