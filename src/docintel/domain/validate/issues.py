"""One problem found in one field of one answer."""

from typing import Literal

from docintel.domain.schema.fields import Strict


class Issue(Strict):
    """`error`: the answer breaks a rule. `warn`: it may be fine, but a person should look."""

    field: str
    rule: str
    severity: Literal["error", "warn"]
    detail: str
