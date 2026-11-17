"""The 12 fields as the UI shows them: a label and a group for each, in schema order."""

from pydantic import BaseModel


class FieldInfo(BaseModel):
    name: str
    label: str
    group: str


GROUPS = {  # the 0d groups, in plain words: group -> (name, label)
    "Basic facts": [
        ("parties", "Parties"),
        ("agreement_date", "Agreement date"),
        ("governing_law", "Governing law"),
    ],
    "Yes or no": [
        ("non_compete", "Non-compete"),
        ("change_of_control", "Change of control"),
        ("anti_assignment", "Anti-assignment"),
    ],
    "Terms": [
        ("renewal_term", "Renewal term"),
        ("notice_period_to_terminate_renewal", "Notice to stop renewal"),
        ("cap_on_liability", "Cap on liability"),
    ],
    "License and IP": [
        ("license_grant", "License grant"),
        ("ip_ownership_assignment", "IP ownership transfer"),
        ("non_transferable_license", "Non-transferable license"),
    ],
}
FIELD_INFO = [
    FieldInfo(name=n, label=lab, group=g) for g, rows in GROUPS.items() for n, lab in rows
]
