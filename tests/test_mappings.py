from hdx.utilities.text import normalise

from hapi.pipelines.utilities.mappings import get_code_from_name


def test_get_code_from_name_org_type():
    org_type_lookup = {
        "Academic / Research": "431",
        "Donor": "433",
        "Embassy": "434",
        "Government": "435",
        "International NGO": "437",
        "International Organization": "438",
        "Media": "439",
        "Military": "440",
        "National NGO": "441",
        "Other": "443",
        "Private sector": "444",
        "Red Cross / Red Crescent": "445",
        "Religious": "446",
        "United Nations": "447",
    }
    org_type_map = {
        "agence un": "447",
        "govt": "435",
        "ingo": "437",
        "mouv. cr": "445",
        "nngo": "441",
        "ong int": "437",
        "ong nat": "441",
        "un agency": "447",
    }
    actual_org_type_lookup = {
        normalise(k): v for k, v in org_type_lookup.items()
    }
    actual_org_type_lookup.update(org_type_map)
    assert (
        get_code_from_name(
            "NATIONAL_NGO",
            actual_org_type_lookup,
        )
        == "441"
    )
    assert (
        get_code_from_name(
            "COOPÉRATION_INTERNATIONALE",
            actual_org_type_lookup,
        )
        is None
    )
    assert get_code_from_name("NGO", actual_org_type_lookup) is None
    assert (
        get_code_from_name(
            "International",
            actual_org_type_lookup,
        )
        is None
    )


def test_get_code_from_name_sector():
    sector_lookup = {
        "Emergency Shelter and NFI": "SHL",
        "Camp Coordination / Management": "CCM",
        "Mine Action": "PRO - MIN",
        "Food Security": "FSC",
        "Water Sanitation Hygiene": "WSH",
        "Logistics": "LOG",
        "Child Protection": "PRO - CPN",
        "Protection": "PRO",
        "Education": "EDU",
        "Nutrition": "NUT",
        "Health": "HEA",
        "Early Recovery": "ERY",
        "Emergency Telecommunications": "TEL",
        "Gender Based Violence": "PRO - GBV",
        "Housing, Land and Property": "PRO - HLP",
    }
    sector_map = {
        "abris": "SHL",
        "cccm": "CCM",
        "coordination": "CCM",
        "education": "EDU",
        "eha": "WSH",
        "erl": "ERY",
        "nutrition": "NUT",
        "operatioanl presence: water, sanitation & hygiene": "WSH",
        "operational presence: education in emergencies": "EDU",
        "operational presence: emergency shelter & non-food items": "SHL",
        "operational presence: food security & agriculture": "FSC",
        "operational presence: health": "HEA",
        "operational presence: nutrition": "NUT",
        "operational presence: protection": "PRO",
        "protection": "PRO",
        "sa": "FSC",
        "sante": "HEA",
        "wash": "WSH",
    }

    actual_sector_lookup = {normalise(k): v for k, v in sector_lookup.items()}
    actual_sector_lookup.update(sector_map)
    assert (
        get_code_from_name("education", actual_sector_lookup, fuzzy_match=True)
        == "EDU"
    )
    assert (
        get_code_from_name(
            "LOGISTIQUE", actual_sector_lookup, fuzzy_match=True
        )
        == "LOG"
    )
    assert get_code_from_name("CCCM", actual_sector_lookup) == "CCM"
    assert get_code_from_name("Santé", actual_sector_lookup) == "HEA"
    actual_sector_lookup["cccm"] = "CCM"
    assert get_code_from_name("CCS", actual_sector_lookup) is None
