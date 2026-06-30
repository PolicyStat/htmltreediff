from unittest.mock import patch

from htmltreediff.text import WordMatcher
from htmltreediff.util import (
    check_text_similarity,
    node_compare,
    parse_minidom,
    walk_dom,
)


def test_node_compare():
    del_node = list(walk_dom(parse_minidom('<del/>')))[-1]
    ins_node = list(walk_dom(parse_minidom('<ins/>')))[-1]
    assert -1 == node_compare(del_node, ins_node)
    assert 1 == node_compare(ins_node, del_node)


def _uses_autojunk(html):
    dom = parse_minidom(html)
    node = dom.documentElement.firstChild
    captured = []
    original_init = WordMatcher.__init__

    def spy_init(self, **kwargs):
        captured.append(kwargs.get('autojunk', True))
        original_init(self, **kwargs)

    with patch.object(WordMatcher, '__init__', spy_init):
        check_text_similarity(node, node, cutoff=0.4)

    return any(captured)


def test_check_text_similarity_autojunk_disabled_for_table_element():
    assert _uses_autojunk('<tbody><tr><td>Some cell text</td></tr></tbody>') is False


def test_check_text_similarity_autojunk_enabled_for_non_table_element():
    assert _uses_autojunk('<p>Some text here</p>') is True
