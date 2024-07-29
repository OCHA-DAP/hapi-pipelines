from hapi.pipelines.database.org import OrgInfo


def check_org_mappings(pipelines):
    org_map = pipelines.org._org_map
    iom = OrgInfo(
        "International Organization for Migration",
        "international organization for migration",
        "IOM",
        "iom",
        "447",
        True,
        True,
    )
    assert org_map[(None, "IOM")] == iom
    assert org_map[(None, "iom")] == iom
    assert (
        org_map[
            (
                None,
                "Organisation Internationale pour les Migrations",
            )
        ]
        == iom
    )
    assert (
        org_map[
            (
                None,
                "organisation internationale pour les migrations",
            )
        ]
        == iom
    )

    iom = OrgInfo(
        "International Organization for Migration",
        "international organization for migration",
        "IOM",
        "iom",
        "447",
        False,
        False,
    )
    assert org_map[(None, "International Organisation for Migrations")] == iom
    assert org_map[(None, "international organisation for migrations")] == iom
    assert org_map[(None, "INTERNATIONALE ORGANISATION FOR MIGRATION")] == iom
    assert org_map[(None, "internationale organisation for migration")] == iom
    assert (
        org_map[
            (
                None,
                "Organisation Internationale des Migrations",
            )
        ]
        == iom
    )
    assert (
        org_map[
            (
                None,
                "organisation internationale des migrations",
            )
        ]
        == iom
    )
    assert (
        org_map[
            (
                None,
                "OIM - International Organization for Migration",
            )
        ]
        == iom
    )
    assert (
        org_map[
            (
                None,
                "oim international organization for migration",
            )
        ]
        == iom
    )

    unicef = OrgInfo(
        "United Nations Children's Fund",
        "united nations childrens fund",
        "UNICEF",
        "unicef",
        "447",
        True,
        True,
    )
    assert org_map[(None, "United Nations Children's Fund")] == unicef
    assert org_map[(None, "united nations childrens fund")] == unicef
    assert org_map[(None, "UNICEF")] == unicef
    assert org_map[(None, "unicef")] == unicef
    assert org_map[(None, "Fonds des Nations Unies pour l'Enfance")] == unicef
    assert org_map[(None, "fonds des nations unies pour lenfance")] == unicef
    assert (
        org_map[
            (
                None,
                "UNICEF - Fondo de las Naciones Unidas para la Infancia",
            )
        ]
        == unicef
    )
    assert (
        org_map[
            (
                None,
                "unicef fondo de las naciones unidas para la infancia",
            )
        ]
        == unicef
    )

    unicef = OrgInfo(
        "United Nations Children's Fund",
        "united nations childrens fund",
        "UNICEF",
        "unicef",
        "447",
        False,
        False,
    )
    assert (
        org_map[(None, "United Nations Children's Emergency Fund")] == unicef
    )
    assert org_map[(None, "united nations childrens emergency fund")] == unicef
    assert org_map[(None, "Fond des Nations Unies pour l'Enfance")] == unicef
    assert org_map[(None, "fond des nations unies pour lenfance")] == unicef
    assert (
        org_map[
            (
                None,
                "United Nations International Childrens Emergency Fund",
            )
        ]
        == unicef
    )
    assert (
        org_map[
            (
                None,
                "united nations international childrens emergency fund",
            )
        ]
        == unicef
    )

    assert org_map[("AFG", "WEWORLD")] == OrgInfo(
        "WEWORLD",
        "weworld",
        "WEWORLD",
        "weworld",
        None,
        True,
        False,
    )

    assert org_map[("NGA", "HECADF")] == OrgInfo(
        "HECADF",
        "hecadf",
        "HECADF",
        "hecadf",
        "441",
        True,
        True,
    )
