from htmltreediff.html import diff


def test_block_tag_rename_shows_no_diff():
    result = diff('<p>foo</p>', '<h2>foo</h2>', textonly=True)
    assert '<del>' not in result
    assert '<ins>' not in result


def test_heading_level_change_shows_no_diff():
    result = diff('<h1>Title</h1>', '<h3>Title</h3>', textonly=True)
    assert '<del>' not in result
    assert '<ins>' not in result


def test_multiple_block_renames_show_no_diff():
    result = diff('<p>hello</p><p>world</p>', '<h1>hello</h1><div>world</div>', textonly=True)
    assert '<del>' not in result
    assert '<ins>' not in result


def test_nested_block_rename_shows_no_diff():
    result = diff('<div><p>hello</p></div>', '<section><p>hello</p></section>', textonly=True)
    assert '<del>' not in result
    assert '<ins>' not in result


def test_block_tag_rename_with_text_change_shows_text_diff():
    result = diff('<p>old text</p>', '<h2>new text</h2>', textonly=True)
    assert result == '<h2><del>old</del><ins>new</ins> text</h2>'


def test_text_change_within_block():
    result = diff(
        '<p>The quick brown fox</p>',
        '<p>The very quick brown fox</p>',
        textonly=True,
    )
    assert result == '<p>The<ins> very</ins> quick brown fox</p>'


def test_inline_formatting_added_shows_no_diff():
    result = diff('<p>foo</p>', '<p><strong>foo</strong></p>', textonly=True)
    assert '<ins>' not in result
    assert '<del>' not in result


def test_inline_formatting_removed_shows_no_diff():
    result = diff('<p><em>foo</em></p>', '<p>foo</p>', textonly=True)
    assert '<ins>' not in result
    assert '<del>' not in result


def test_added_block_shows_insertion():
    result = diff('<p>one</p>', '<p>one</p><p>two</p>', textonly=True)
    assert result == '<p>one</p><p><ins>two</ins></p>'


def test_removed_block_shows_deletion():
    result = diff(
        '<p>alpha</p><p>beta</p><p>gamma</p>',
        '<p>alpha</p><p>gamma</p>',
        textonly=True,
    )
    assert result == '<p>alpha</p><del class="block-deleted">beta </del><p>gamma</p>'


def test_table_cell_text_change():
    result = diff(
        '<table><tr><td>... A ...</td></tr></table>',
        '<table><tr><td>... B ...</td></tr></table>',
        textonly=True,
    )
    assert result == '<table><tr><td>... <del>A</del><ins>B</ins> ...</td></tr></table>'


def test_list_item_text_change():
    result = diff(
        '<ol><li>AAA</li><li>BBB</li></ol>',
        '<ol><li>ZZZ</li><li>BBB</li></ol>',
        textonly=True,
    )
    assert result == '<ol><li><del>AAA</del><ins>ZZZ</ins></li><li>BBB</li></ol>'


def test_br_treated_as_space_separator():
    result = diff('<p>A<br/>B</p>', '<p>A<br/>B</p>', textonly=True)
    assert result == '<p>A<br/>B</p>'


def test_br_with_text_change_after_br():
    result = diff('<p>pizza<br/>slice</p>', '<p>pizza<br/>pie</p>', textonly=True)
    assert result == '<p>pizza<br/><del>slice</del><ins>pie</ins></p>'


def test_words_not_concatenated_across_block_boundaries():
    result = diff('<p>incident</p><p>WHEN</p>', '<p>incident</p><p>WHEN</p>', textonly=True)
    assert result == '<p>incident</p><p>WHEN</p>'


def test_text_change_in_second_block():
    result = diff('<p>hello</p><p>world</p>', '<p>hello</p><p>earth</p>', textonly=True)
    assert result == '<p>hello</p><p><del>world</del><ins>earth</ins></p>'


def test_plaintext_mode_takes_precedence_over_textonly():
    result = diff('hello world', 'hello brave world', plaintext=True, textonly=True)
    assert result == 'hello <ins>brave </ins>world'
