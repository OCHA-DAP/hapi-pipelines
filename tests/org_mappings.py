from typing import List, Tuple

from hapi.pipelines.database.org import OrgInfo


def check_org_mappings(pipelines) -> List[Tuple]:
    org_map = pipelines.org._org_map
    comparisons = []

    # IOM complete and incomplete
    iom_complete = OrgInfo(
        canonical_name="International Organization for Migration",
        normalised_name="international organization for migration",
        acronym="IOM",
        normalised_acronym="iom",
        type_code="447",
        used=True,
        complete=True,
    )
    comparisons.extend(
        [
            (org_map[(None, "IOM")], iom_complete),
            (org_map[(None, "iom")], iom_complete),
            (
                org_map[
                    (None, "Organisation Internationale pour les Migrations")
                ],
                iom_complete,
            ),
            (
                org_map[
                    (None, "organisation internationale pour les migrations")
                ],
                iom_complete,
            ),
        ]
    )

    iom_incomplete = OrgInfo(
        canonical_name="International Organization for Migration",
        normalised_name="international organization for migration",
        acronym="IOM",
        normalised_acronym="iom",
        type_code="447",
        used=False,
        complete=False,
    )

    comparisons.extend(
        [
            (
                org_map[(None, "International Organisation for Migrations")],
                iom_incomplete,
            ),
            (
                org_map[(None, "international organisation for migrations")],
                iom_incomplete,
            ),
            (
                org_map[(None, "INTERNATIONALE ORGANISATION FOR MIGRATION")],
                iom_incomplete,
            ),
            (
                org_map[(None, "internationale organisation for migration")],
                iom_incomplete,
            ),
            (
                org_map[(None, "Organisation Internationale des Migrations")],
                iom_incomplete,
            ),
            (
                org_map[(None, "organisation internationale des migrations")],
                iom_incomplete,
            ),
            (
                org_map[
                    (None, "OIM - International Organization for Migration")
                ],
                iom_incomplete,
            ),
            (
                org_map[
                    (None, "oim international organization for migration")
                ],
                iom_incomplete,
            ),
        ]
    )

    # UNICEF complete and incomplete
    unicef_complete = OrgInfo(
        canonical_name="United Nations Children's Fund",
        normalised_name="united nations childrens fund",
        acronym="UNICEF",
        normalised_acronym="unicef",
        type_code="447",
        used=True,
        complete=True,
    )
    comparisons.extend(
        [
            (
                org_map[(None, "United Nations Children's Fund")],
                unicef_complete,
            ),
            (
                org_map[(None, "united nations childrens fund")],
                unicef_complete,
            ),
            (org_map[(None, "UNICEF")], unicef_complete),
            (org_map[(None, "unicef")], unicef_complete),
            (
                org_map[(None, "Fonds des Nations Unies pour l'Enfance")],
                unicef_complete,
            ),
            (
                org_map[(None, "fonds des nations unies pour lenfance")],
                unicef_complete,
            ),
            (
                org_map[
                    (
                        None,
                        "UNICEF - Fondo de las Naciones Unidas para la Infancia",
                    )
                ],
                unicef_complete,
            ),
            (
                org_map[
                    (
                        None,
                        "unicef fondo de las naciones unidas para la infancia",
                    )
                ],
                unicef_complete,
            ),
        ]
    )

    unicef_incomplete = OrgInfo(
        canonical_name="United Nations Children's Fund",
        normalised_name="united nations childrens fund",
        acronym="UNICEF",
        normalised_acronym="unicef",
        type_code="447",
        used=False,
        complete=False,
    )
    comparisons.extend(
        [
            (
                org_map[(None, "Fond des Nations Unies pour l'Enfance")],
                unicef_incomplete,
            ),
            (
                org_map[(None, "fond des nations unies pour lenfance")],
                unicef_incomplete,
            ),
            (
                org_map[
                    (
                        None,
                        "United Nations International Childrens Emergency Fund",
                    )
                ],
                unicef_incomplete,
            ),
            (
                org_map[
                    (
                        None,
                        "united nations international childrens emergency fund",
                    )
                ],
                unicef_incomplete,
            ),
        ]
    )

    # Misc orgs
    medair = OrgInfo(
        canonical_name="MEDAIR",
        normalised_name="medair",
        acronym="MEDAIR",
        normalised_acronym="medair",
        type_code=None,
        used=True,
        complete=False,
    )
    street_child = OrgInfo(
        canonical_name="Street Child",
        normalised_name="street child",
        acronym="Street Child",
        normalised_acronym="street child",
        type_code="437",
        used=True,
        complete=True,
    )
    comparisons.extend(
        [
            (org_map[("AFG", "MEDAIR")], medair),
            (org_map[("NGA", "Street Child")], street_child),
        ]
    )

    return comparisons
