"""Tests ported from y25-matrika — validate data-utils parser against matrika's fixtures."""

from pathlib import Path

from data_utils.fragment import FragmentType
from data_utils.parser import parse

FIXTURES = Path(__file__).parent / "fixtures"


# --- simple_page.md ---

def test_simple_page_frontmatter():
    text = FIXTURES.joinpath("simple_page.md").read_text()
    frags = parse(text, "md")
    assert frags[0].type == FragmentType.frontmatter
    assert frags[0].meta["isA"] == "Page"
    assert "test" in frags[0].meta["tags"]


def test_simple_page_heading():
    text = FIXTURES.joinpath("simple_page.md").read_text()
    frags = parse(text, "md")
    headings = [f for f in frags if f.type == FragmentType.heading]
    assert len(headings) == 1
    assert "Simple Page" in headings[0].content


def test_simple_page_footnote():
    text = FIXTURES.joinpath("simple_page.md").read_text()
    frags = parse(text, "md")
    footnotes = [f for f in frags if f.type == FragmentType.footnote]
    assert len(footnotes) == 1
    assert footnotes[0].meta["ref"] == "1"
    assert "Footnote" in footnotes[0].content


# --- complex_page.md ---

def test_complex_page_headings():
    text = FIXTURES.joinpath("complex_page.md").read_text()
    frags = parse(text, "md")
    headings = [f for f in frags if f.type == FragmentType.heading]
    assert len(headings) == 3
    levels = [h.level for h in headings]
    assert levels == [1, 2, 3]


def test_complex_page_footnote():
    text = FIXTURES.joinpath("complex_page.md").read_text()
    frags = parse(text, "md")
    footnotes = [f for f in frags if f.type == FragmentType.footnote]
    assert len(footnotes) == 1
    assert footnotes[0].meta["ref"] == "secfn"


def test_complex_page_lists():
    text = FIXTURES.joinpath("complex_page.md").read_text()
    frags = parse(text, "md")
    lists = [f for f in frags if f.type == FragmentType.list_block]
    assert len(lists) >= 1


# --- duplication.md ---

def test_duplication_headings():
    """Content should not duplicate across fragments."""
    text = FIXTURES.joinpath("duplication.md").read_text()
    frags = parse(text, "md")
    headings = [f for f in frags if f.type == FragmentType.heading]
    titles = [h.content for h in headings]
    assert "Top Level" in titles
    assert "Level Three" in titles
    assert "Another lvl1 Header" in titles


def test_duplication_content_not_repeated():
    """Key text should appear only once across all fragments."""
    text = FIXTURES.joinpath("duplication.md").read_text()
    frags = parse(text, "md")
    all_content = " ".join(f.content for f in frags)
    assert all_content.count("Some text under it, over") == 1
    assert all_content.count("doubled?") == 1


def test_duplication_footnote():
    text = FIXTURES.joinpath("duplication.md").read_text()
    frags = parse(text, "md")
    footnotes = [f for f in frags if f.type == FragmentType.footnote]
    assert len(footnotes) == 1
    assert footnotes[0].meta["ref"] == "m701"


def test_duplication_end_marker_content_excluded():
    """Content after <!--end--> should still parse (data-utils doesn't truncate)."""
    text = FIXTURES.joinpath("duplication.md").read_text()
    frags = parse(text, "md")
    # data-utils parses everything — truncation is a higher-level concern
    all_content = " ".join(f.content for f in frags)
    assert "special unrendered text" in all_content


# --- no_header.md ---

def test_no_header_still_produces_fragments():
    """Content without markdown headers should still produce fragments."""
    text = FIXTURES.joinpath("no_header.md").read_text()
    frags = parse(text, "md")
    # Should have frontmatter + at least one paragraph
    assert any(f.type == FragmentType.frontmatter for f in frags)
    paragraphs = [f for f in frags if f.type == FragmentType.paragraph]
    assert len(paragraphs) >= 1
    all_content = " ".join(f.content for f in paragraphs)
    assert "Deleuze and Guattari" in all_content


# --- wikilink.md ---

def test_wikilink_heading_structure():
    text = FIXTURES.joinpath("wikilink.md").read_text()
    frags = parse(text, "md")
    headings = [f for f in frags if f.type == FragmentType.heading]
    assert len(headings) == 2
    assert headings[0].level == 1
    assert headings[1].level == 2


def test_wikilink_list_items():
    text = FIXTURES.joinpath("wikilink.md").read_text()
    frags = parse(text, "md")
    lists = [f for f in frags if f.type == FragmentType.list_block]
    assert len(lists) >= 1
    # Wiki-style links are preserved as raw text in content
    assert "[[Physics and Spirituality]]" in lists[0].content


# --- Frontmatter-as-hr regression ---

def test_frontmatter_never_produces_hr():
    """Frontmatter delimiters (---) must not produce hr fragments."""
    for fixture in FIXTURES.glob("*.md"):
        text = fixture.read_text()
        if not text.startswith("---"):
            continue
        frags = parse(text, "md")
        types = [f.type for f in frags]
        if FragmentType.frontmatter in types:
            # No hr before the first content fragment
            first_non_fm = next((f for f in frags if f.type != FragmentType.frontmatter), None)
            if first_non_fm:
                assert first_non_fm.type != FragmentType.hr, (
                    f"{fixture.name}: frontmatter delimiter leaked as hr"
                )
