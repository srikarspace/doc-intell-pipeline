"""Prompt and message rules. No network, no key."""

from hashlib import sha256

import pytest

from docintel.domain.extract.extract import PLACEHOLDER, PROMPTS, build_messages, load_prompt
from docintel.domain.schema.fields import ContractFields

TEXT = 'Section {1}: "Licensor" shall {not} assign.\n'  # braces, quotes and a newline


def test_every_version_has_both_files():
    versions = [p.name for p in PROMPTS.iterdir() if p.is_dir()]
    assert versions
    for version in versions:
        system, user = load_prompt(version)
        assert system.strip()
        assert user.count(PLACEHOLDER) == 1


def test_contract_text_goes_in_unchanged():
    messages = build_messages(TEXT, "v1")
    assert [m["role"] for m in messages] == ["system", "user"]
    assert TEXT in messages[1]["content"]
    assert PLACEHOLDER not in messages[1]["content"]


def test_unknown_version_fails():
    with pytest.raises(FileNotFoundError):
        build_messages(TEXT, "v999")


def test_every_prompt_names_every_field():
    for version in [p.name for p in PROMPTS.iterdir() if p.is_dir()]:
        system, _ = load_prompt(version)
        for field in ContractFields.model_fields:
            assert f"- {field}:" in system, f"{version} does not define {field}"


def test_v1_never_changes():
    system, _ = load_prompt("v1")
    assert sha256(system.encode()).hexdigest()[:12] == "e4bcfc8ac5b5"
