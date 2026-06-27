# Tests for the textonly=True diff mode.
from htmltreediff.html import diff


def test_block_tag_rename_no_change():
    """A block tag rename with same text should show no changes."""
    assert diff('<p>foo</p>', '<h2>foo</h2>', textonly=True) == '<p>foo</p>'


def test_block_tag_rename_with_text_change():
    """Block tag rename with different text still shows text change."""
    result = diff('<p>old text</p>', '<h2>new text</h2>', textonly=True)
    assert '<del>old</del>' in result
    assert '<ins>new</ins>' in result


def test_inline_formatting_added():
    """Adding inline formatting (strong) shows as a change."""
    result = diff('<p>foo</p>', '<p><strong>foo</strong></p>', textonly=True)
    assert '<ins>' in result or '<del>' in result


def test_inline_formatting_removed():
    """Removing inline formatting (em) shows as a change."""
    result = diff('<p><em>foo</em></p>', '<p>foo</p>', textonly=True)
    assert '<ins>' in result or '<del>' in result


def test_span_preserved_in_textonly_mode():
    """Span tags are preserved and diffed in textonly mode."""
    result = diff('<p>foo</p>', '<p><span class="x">foo</span></p>',
                  textonly=True)
    assert 'span' in result


def test_multiple_blocks_same_text():
    """Multiple block elements with same text show no changes."""
    result = diff('<p>hello</p><p>world</p>',
                  '<h1>hello</h1><div>world</div>', textonly=True)
    assert '<del>' not in result
    assert '<ins>' not in result


def test_nested_block_rename():
    """Nested block tag rename with same content shows no changes."""
    result = diff('<div><p>hello</p></div>',
                  '<section><p>hello</p></section>', textonly=True)
    assert '<del>' not in result
    assert '<ins>' not in result


def test_textonly_text_diff_within_same_block():
    """Text changes within a block element are shown."""
    result = diff('<p>The quick brown fox</p>',
                  '<p>The very quick brown fox</p>', textonly=True)
    assert '<ins>' in result
    assert 'very' in result


def test_textonly_does_not_affect_normal_mode():
    """Normal mode (textonly=False) still shows block tag changes."""
    result = diff('<p>foo</p>', '<h2>foo</h2>', textonly=False)
    assert '<del>' in result
    assert '<ins>' in result


def test_textonly_with_table():
    """Table content changes still work in textonly mode."""
    result = diff(
        '<table><tr><td>... A ...</td></tr></table>',
        '<table><tr><td>... B ...</td></tr></table>',
        textonly=True,
    )
    assert '<del>A</del>' in result
    assert '<ins>B</ins>' in result


def test_textonly_with_list():
    """List content changes still work in textonly mode."""
    result = diff(
        '<ol><li>AAA</li><li>BBB</li></ol>',
        '<ol><li>ZZZ</li><li>BBB</li></ol>',
        textonly=True,
    )
    assert '<del>AAA</del>' in result
    assert '<ins>ZZZ</ins>' in result


def test_textonly_plaintext_mode_unaffected():
    """Plaintext mode is not affected by textonly."""
    result = diff('The quick brown fox', 'The very quick brown fox',
                  plaintext=True, textonly=True)
    assert '<ins> very</ins>' in result


def test_textonly_heading_levels():
    """Changing heading levels with same text shows no change."""
    result = diff('<h1>Title</h1>', '<h3>Title</h3>', textonly=True)
    assert '<del>' not in result
    assert '<ins>' not in result


def test_textonly_add_new_block():
    """Adding a new block element still shows as insertion."""
    result = diff('<p>one</p>', '<p>one</p><p>two</p>', textonly=True)
    assert '<ins>' in result
    assert 'two' in result


def test_textonly_remove_block():
    """Removing a block element still shows as deletion."""
    result = diff('<p>one</p><p>two</p>', '<p>one</p>', textonly=True)
    assert '<del>' in result
    assert 'two' in result
