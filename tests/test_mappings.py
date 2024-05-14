from hapi.pipelines.utilities.mappings import get_code_from_name


def test_get_code_from_name():
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
    assert get_code_from_name(
        "NATIONAL_NGO", org_type_lookup, org_type_map
    ) == ("441", "national ngo", True)
    assert get_code_from_name(
        "COOPÉRATION_INTERNATIONALE", org_type_lookup, org_type_map
    ) == (None, "cooperation internationale", False)
    assert get_code_from_name("NGO", org_type_lookup, org_type_map) == (
        None,
        "ngo",
        False,
    )
    assert get_code_from_name(
        "International", org_type_lookup, org_type_map
    ) == (None, "international", False)
    assert get_code_from_name("LOGISTIQUE", sector_lookup, sector_map) == (
        "LOG",
        "logistique",
        True,
    )
    assert get_code_from_name("CCCM", sector_lookup, sector_map) == (
        "CCM",
        "cccm",
        False,
    )
    assert get_code_from_name("Santé", sector_lookup, sector_map) == (
        "HEA",
        "sante",
        False,
    )
    sector_lookup["cccm"] = "CCM"
    assert get_code_from_name("CCS", sector_lookup, sector_map) == (
        None,
        "ccs",
        False,
    )