"""Tests for data_utils.parser."""

from pathlib import Path

from data_utils.fragment import FragmentType
from data_utils.parser import parse

FIXTURES = Path(__file__).parent / "fixtures"


def test_markdown_frontmatter():
    text = FIXTURES.joinpath("sample.md").read_text()
    frags = parse(text, "md")
    assert frags[0].type == FragmentType.frontmatter
    assert frags[0].meta["author"] == "claude"
    assert frags[0].meta["status"] == "draft"
    assert frags[0].line_start == 1


def test_markdown_heading():
    text = FIXTURES.joinpath("sample.md").read_text()
    frags = parse(text, "md")
    headings = [f for f in frags if f.type == FragmentType.heading]
    assert len(headings) == 3
    assert headings[0].content == "Sample Report"
    assert headings[0].level == 1
    assert headings[1].content == "Section Two"
    assert headings[1].level == 2
    assert headings[2].content == "Code Example"
    assert headings[2].level == 3


def test_markdown_paragraph():
    text = FIXTURES.joinpath("sample.md").read_text()
    frags = parse(text, "md")
    paras = [f for f in frags if f.type == FragmentType.paragraph]
    assert len(paras) >= 1
    assert "bold text" in paras[0].content


def test_markdown_list():
    text = FIXTURES.joinpath("sample.md").read_text()
    frags = parse(text, "md")
    lists = [f for f in frags if f.type == FragmentType.list_block]
    assert len(lists) == 1
    assert "item one" in lists[0].content
    assert "item three" in lists[0].content


def test_markdown_code_block():
    text = FIXTURES.joinpath("sample.md").read_text()
    frags = parse(text, "md")
    code = [f for f in frags if f.type == FragmentType.code_block]
    assert len(code) == 1
    assert code[0].lang == "python"
    assert "hello" in code[0].content


def test_markdown_mermaid_block():
    text = FIXTURES.joinpath("sample.md").read_text()
    frags = parse(text, "md")
    mermaids = [f for f in frags if f.type == FragmentType.mermaid]
    assert len(mermaids) == 1
    assert "graph TD" in mermaids[0].content
    assert mermaids[0].lang == "mermaid"


def test_markdown_hr():
    text = FIXTURES.joinpath("sample.md").read_text()
    frags = parse(text, "md")
    hrs = [f for f in frags if f.type == FragmentType.hr]
    assert len(hrs) == 1


def test_markdown_footnotes():
    text = FIXTURES.joinpath("sample.md").read_text()
    frags = parse(text, "md")
    footnotes = [f for f in frags if f.type == FragmentType.footnote]
    assert len(footnotes) == 2
    assert footnotes[0].meta["ref"] == "3:abcd1234"
    assert footnotes[0].meta["by"] == "exrhizo"
    assert footnotes[0].content == "This is a general comment"
    assert footnotes[1].meta["ref"] == "18:ef567890"
    assert "by" not in footnotes[1].meta


def test_frontmatter_not_rendered_as_hr():
    """Frontmatter should be parsed as frontmatter, not as hr."""
    text = "---\ntitle: test\n---\n\n# Hello"
    frags = parse(text, "md")
    types = [f.type for f in frags]
    assert FragmentType.frontmatter in types
    assert FragmentType.hr not in types


def test_yaml_file():
    text = FIXTURES.joinpath("sample.yaml").read_text()
    frags = parse(text, "yaml")
    assert len(frags) == 1
    assert frags[0].type == FragmentType.yaml_block
    assert "name: test-project" in frags[0].content


def test_mermaid_file():
    text = FIXTURES.joinpath("sample.mermaid").read_text()
    frags = parse(text, "mermaid")
    types = [f.type for f in frags]
    assert FragmentType.frontmatter in types
    mermaids = [f for f in frags if f.type == FragmentType.mermaid]
    assert len(mermaids) == 2


def test_fragment_ids_are_stable():
    text = "# Hello\n\nWorld"
    a = parse(text, "md")
    b = parse(text, "md")
    assert [f.id for f in a] == [f.id for f in b]


def test_fragment_ids_change_with_content():
    a = parse("# Hello", "md")
    b = parse("# Goodbye", "md")
    assert a[0].id != b[0].id


def test_empty_text():
    assert parse("", "md") == []
    assert parse("", "yaml") == []
    assert parse("", "mermaid") == []
    assert parse("   \n\n  ", "md") == []
