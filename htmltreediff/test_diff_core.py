# coding: utf-8
from unittest.mock import patch

from nose.tools import assert_equal

from htmltreediff.diff_core import (
    _has_fuzzy_hash_collisions,
    build_pairwise_match_matrix,
    compute_longest_common_subsequence_lengths_table,
    fuzzy_match_blocks,
    group_consecutive_pairs_into_blocks,
    traceback_longest_common_subsequence_matched_pairs,
    Differ,
)
from htmltreediff.util import parse_minidom


def get_dom_nodes(html):
    dom = parse_minidom('<section>{}</section>'.format(html))
    return list(dom.getElementsByTagName('section')[0].childNodes)


# --- _has_fuzzy_hash_collisions ---


def test_has_fuzzy_hash_collisions_no_children():
    assert_equal(_has_fuzzy_hash_collisions([]), False)


def test_all_distinct_tags_dont_have_collisions():
    assert_equal(_has_fuzzy_hash_collisions(get_dom_nodes('<p>a</p><h1>b</h1>')), False)


def test_same_tag_twice_has_collision():
    assert_equal(_has_fuzzy_hash_collisions(get_dom_nodes('<p>a</p><p>b</p>')), True)


def test_text_nodes_ignored_in_collision_check():
    assert_equal(_has_fuzzy_hash_collisions(get_dom_nodes('hello <p>a</p><h1>b</h1>')), False)


# --- build_pairwise_match_matrix ---


def test_build_pairwise_match_matrix_no_matches():
    assert_equal(
        build_pairwise_match_matrix(['a', 'b'], ['c', 'd']),
        [[False, False], [False, False]],
    )


def test_build_pairwise_match_matrix_some_matches():
    assert_equal(
        build_pairwise_match_matrix(['a', 'b'], ['b', 'c']),
        [[False, False], [True, False]],
    )


def test_build_pairwise_match_matrix_empty():
    assert_equal(build_pairwise_match_matrix([], []), [])


# --- compute_longest_common_subsequence_lengths_table ---


def test_lcs_lengths_no_matches():
    match_matrix = [[False, False], [False, False]]
    lcs_lengths = compute_longest_common_subsequence_lengths_table(match_matrix)
    assert_equal(lcs_lengths[0][0], 0)


def test_lcs_lengths_diagonal_matches_accumulate():
    match_matrix = [[True, False], [False, True]]
    lcs_lengths = compute_longest_common_subsequence_lengths_table(match_matrix)
    assert_equal(lcs_lengths[0][0], 2)


# --- traceback_longest_common_subsequence_matched_pairs ---


def test_traceback_no_matches_returns_no_pairs():
    match_matrix = [[False, False], [False, False]]
    lcs_lengths = compute_longest_common_subsequence_lengths_table(match_matrix)
    assert_equal(
        traceback_longest_common_subsequence_matched_pairs(match_matrix, lcs_lengths),
        [],
    )


def test_traceback_two_diagonal_matches_returns_correct_pairs():
    match_matrix = [[True, False], [False, True]]
    lcs_lengths = compute_longest_common_subsequence_lengths_table(match_matrix)
    assert_equal(
        traceback_longest_common_subsequence_matched_pairs(match_matrix, lcs_lengths),
        [(0, 0), (1, 1)],
    )


def test_traceback_skips_unmatched_old_node_to_reach_best_lcs():
    # old = ['b', 'a'], new = ['a']
    # old[0] does not match; old[1] does: result should be [(1, 0)], not []
    match_matrix = [[False], [True]]
    lcs_lengths = compute_longest_common_subsequence_lengths_table(match_matrix)
    assert_equal(
        traceback_longest_common_subsequence_matched_pairs(match_matrix, lcs_lengths),
        [(1, 0)],
    )


# --- group_consecutive_pairs_into_blocks ---


def test_group_no_pairs_produces_only_sentinel():
    assert_equal(
        group_consecutive_pairs_into_blocks([], 2, 3),
        [(2, 3, 0)],
    )


def test_group_consecutive_pairs_merged_into_one_block():
    assert_equal(
        group_consecutive_pairs_into_blocks([(0, 0), (1, 1)], 2, 2),
        [(0, 0, 2), (2, 2, 0)],
    )


def test_group_non_consecutive_pairs_become_separate_blocks():
    assert_equal(
        group_consecutive_pairs_into_blocks([(0, 0), (2, 2)], 3, 3),
        [(0, 0, 1), (2, 2, 1), (3, 3, 0)],
    )


# --- fuzzy_match_blocks ---


def test_fuzzy_match_blocks_empty_old():
    assert_equal(fuzzy_match_blocks([], get_dom_nodes('<p>hello</p>')), [(0, 1, 0)])


def test_fuzzy_match_blocks_empty_new():
    assert_equal(fuzzy_match_blocks(get_dom_nodes('<p>hello</p>'), []), [(1, 0, 0)])


def test_fuzzy_match_blocks_similar_text_same_tag_matches():
    old = get_dom_nodes('<p>Hello world</p>')
    new = get_dom_nodes('<p>Hello earth</p>')
    assert_equal(fuzzy_match_blocks(old, new), [(0, 0, 1), (1, 1, 0)])


def test_fuzzy_match_blocks_different_tag_does_not_match():
    old = get_dom_nodes('<p>Hello world</p>')
    new = get_dom_nodes('<h1>Hello world</h1>')
    assert_equal(fuzzy_match_blocks(old, new), [(1, 1, 0)])


def test_fuzzy_match_blocks_unmatched_node_excluded_from_blocks():
    # old[0] and old[1] fuzzy-match new[0] and new[1]; old[2] has no match
    old = get_dom_nodes('<p>Hello world</p><p>Foo bar</p><h2>Other</h2>')
    new = get_dom_nodes('<p>Hello earth</p><p>Foo bar</p>')
    assert_equal(fuzzy_match_blocks(old, new), [(0, 0, 2), (3, 2, 0)])


# --- table-context restriction for fuzzy_match_blocks ---


def _make_differ():
    empty = parse_minidom('<html></html>')
    return Differ(empty, empty)


def test_fuzzy_match_not_called_outside_table_context():
    old = get_dom_nodes('<p>Alpha paragraph.</p><p>Beta paragraph.</p>')
    new = get_dom_nodes('<p>Alpha changed.</p><p>Beta changed.</p>')
    with patch('htmltreediff.diff_core.fuzzy_match_blocks', wraps=fuzzy_match_blocks) as spy:
        _make_differ().match_children(old, new, in_table_context=False)
    spy.assert_not_called()


def test_fuzzy_match_called_inside_table_context():
    old = get_dom_nodes('<tr><td>Row one old</td></tr><tr><td>Row two old</td></tr>')
    new = get_dom_nodes('<tr><td>Row one new</td></tr><tr><td>Row two new</td></tr>')
    with patch('htmltreediff.diff_core.fuzzy_match_blocks', wraps=fuzzy_match_blocks) as spy:
        _make_differ().match_children(old, new, in_table_context=True)
    spy.assert_called()


def test_fuzzy_match_not_called_when_gap_exceeds_size_limit():
    # 3 old x 3 new = gap size 9; set limit to 4 so it falls back.
    old = get_dom_nodes(
        '<tr><td>A</td></tr>'
        '<tr><td>B</td></tr>'
        '<tr><td>C</td></tr>'
    )
    new = get_dom_nodes(
        '<tr><td>X</td></tr>'
        '<tr><td>Y</td></tr>'
        '<tr><td>Z</td></tr>'
    )
    with patch('htmltreediff.diff_core.fuzzy_match_blocks', wraps=fuzzy_match_blocks) as spy:
        with patch('htmltreediff.diff_core.FUZZY_MATCH_SIZE_LIMIT', 4):
            _make_differ().match_children(old, new, in_table_context=True)
    spy.assert_not_called()


def test_fuzzy_match_called_when_gap_within_size_limit():
    # 3 old x 3 new = gap size 9; set limit to 9 so it proceeds.
    old = get_dom_nodes(
        '<tr><td>A</td></tr>'
        '<tr><td>B</td></tr>'
        '<tr><td>C</td></tr>'
    )
    new = get_dom_nodes(
        '<tr><td>X</td></tr>'
        '<tr><td>Y</td></tr>'
        '<tr><td>Z</td></tr>'
    )
    with patch('htmltreediff.diff_core.fuzzy_match_blocks', wraps=fuzzy_match_blocks) as spy:
        with patch('htmltreediff.diff_core.FUZZY_MATCH_SIZE_LIMIT', 9):
            _make_differ().match_children(old, new, in_table_context=True)
    spy.assert_called()
