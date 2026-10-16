"""The 12 fields as Pydantic models. The JSON schema we send to the model is built from these."""

from pydantic import BaseModel, ConfigDict, Field


class Strict(BaseModel):
    """Base for every model we send to the LLM: no unknown keys, no type guessing."""

    model_config = ConfigDict(extra="forbid", strict=True)


QUOTES = Field(description="Exact text copied from the contract. Empty list if not found.")


class Clause(Strict):
    """A yes/no field: the clause is there or not. `found` is the answer."""

    quotes: list[str] = QUOTES
    found: bool


class Text(Strict):
    """A field with one short answer, like a date, a state or a term."""

    quotes: list[str] = QUOTES
    value: str | None
    found: bool


class Names(Strict):
    """A field with a list of answers, like the parties."""

    quotes: list[str] = QUOTES
    value: list[str]
    found: bool


class ContractFields(Strict):
    """All 12 fields for one contract."""

    parties: Names
    agreement_date: Text
    governing_law: Text
    non_compete: Clause
    change_of_control: Clause
    anti_assignment: Clause
    renewal_term: Text
    notice_period_to_terminate_renewal: Text
    cap_on_liability: Text
    license_grant: Clause
    ip_ownership_assignment: Clause
    non_transferable_license: Clause


CUAD_CATEGORY = {  # attribute name -> CUAD category, so 1b can join on labels.category
    "parties": "Parties",
    "agreement_date": "Agreement Date",
    "governing_law": "Governing Law",
    "non_compete": "Non-Compete",
    "change_of_control": "Change Of Control",
    "anti_assignment": "Anti-Assignment",
    "renewal_term": "Renewal Term",
    "notice_period_to_terminate_renewal": "Notice Period To Terminate Renewal",
    "cap_on_liability": "Cap On Liability",
    "license_grant": "License Grant",
    "ip_ownership_assignment": "Ip Ownership Assignment",
    "non_transferable_license": "Non-Transferable License",
}
