"""Agent context files hold their shape: the root file stays short, CLAUDE.md
stays a pointer to it, and the skill list cannot drift from the directories."""

import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
AGENTS = ROOT / "AGENTS.md"
SKILLS = ROOT / ".claude" / "skills"

MAX_AGENTS_LINES = 200
MAX_SKILL_BODY_LINES = 500
MAX_DESCRIPTION_CHARS = 1024
NAME_PATTERN = re.compile(r"^[a-z0-9-]{1,64}$")


def skill_files():
    return sorted(SKILLS.glob("*/SKILL.md"))


def parse_frontmatter(path):
    lines = path.read_text().splitlines()
    assert lines and lines[0] == "---", f"{path} does not open with frontmatter"
    end = lines.index("---", 1)
    fields = {}
    for line in lines[1:end]:
        key, _, value = line.partition(":")
        fields[key.strip()] = value.strip()
    return fields, lines[end + 1 :]


def test_agents_file_stays_within_its_length_budget():
    lines = AGENTS.read_text().splitlines()
    assert len(lines) <= MAX_AGENTS_LINES


def test_claude_md_is_only_a_pointer_to_agents_md():
    assert (ROOT / "CLAUDE.md").read_text().strip() == "@AGENTS.md"


def test_listed_skills_are_exactly_the_skills_that_exist():
    listed = set(
        re.findall(
            r"^- `([a-z0-9-]+)`",
            AGENTS.read_text().split("<!-- skills -->")[1].split("<!-- /skills -->")[0],
            re.MULTILINE,
        )
    )
    assert listed
    assert listed == {path.parent.name for path in skill_files()}


@pytest.mark.parametrize("path", skill_files(), ids=lambda path: path.parent.name)
def test_skill_frontmatter_and_body_are_within_the_standard(path):
    fields, body = parse_frontmatter(path)

    assert fields.get("name") == path.parent.name
    assert NAME_PATTERN.match(fields["name"])

    description = fields.get("description", "")
    assert description
    assert len(description) <= MAX_DESCRIPTION_CHARS

    assert len(body) <= MAX_SKILL_BODY_LINES
