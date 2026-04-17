from nose.tools import assert_equal

from htmltreediff.diff_core import (
    _has_fuzzy_hash_collisions,
    build_pairwise_match_matrix,
    compute_longest_common_subsequence_lengths_table,
    fuzzy_match_blocks,
    group_consecutive_pairs_into_blocks,
    traceback_longest_common_subsequence_matched_pairs,
)
from htmltreediff.util import parse_minidom


def children_of(html):
    dom = parse_minidom('<section>{}</section>'.format(html))
    return list(dom.getElementsByTagName('section')[0].childNodes)


# --- _has_fuzzy_hash_collisions ---


def test_has_fuzzy_hash_collisions_no_children():
    assert_equal(_has_fuzzy_hash_collisions([]), False)


def test_has_fuzzy_hash_collisions_all_distinct_tags():
    # <p> and <h1> have different tags so different hashes — no collision
    assert_equal(_has_fuzzy_hash_collisions(children_of('<p>a</p><h1>b</h1>')), False)


def test_has_fuzzy_hash_collisions_same_tag_twice_is_collision():
    # Two <p> elements: same tag → same FuzzyHashableTree hash → collision
    assert_equal(_has_fuzzy_hash_collisions(children_of('<p>a</p><p>b</p>')), True)


def test_has_fuzzy_hash_collisions_text_nodes_ignored():
    # Text nodes are skipped; only two distinct element tags → no collision
    assert_equal(_has_fuzzy_hash_collisions(children_of('hello <p>a</p><h1>b</h1>')), False)


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


def test_traceback_no_matches():
    match_matrix = [[False, False], [False, False]]
    lcs_lengths = compute_longest_common_subsequence_lengths_table(match_matrix)
    assert_equal(
        traceback_longest_common_subsequence_matched_pairs(match_matrix, lcs_lengths),
        [],
    )


def test_traceback_two_diagonal_matches():
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
    assert_equal(fuzzy_match_blocks([], children_of('<p>hello</p>')), [(0, 1, 0)])


def test_fuzzy_match_blocks_empty_new():
    assert_equal(fuzzy_match_blocks(children_of('<p>hello</p>'), []), [(1, 0, 0)])


def test_fuzzy_match_blocks_similar_text_same_tag_matches():
    old = children_of('<p>Hello world</p>')
    new = children_of('<p>Hello earth</p>')
    assert_equal(fuzzy_match_blocks(old, new), [(0, 0, 1), (1, 1, 0)])


def test_fuzzy_match_blocks_different_tag_does_not_match():
    old = children_of('<p>Hello world</p>')
    new = children_of('<h1>Hello world</h1>')
    assert_equal(fuzzy_match_blocks(old, new), [(1, 1, 0)])


def test_fuzzy_match_blocks_unmatched_node_excluded_from_blocks():
    # old[0] and old[1] fuzzy-match new[0] and new[1]; old[2] has no match
    old = children_of('<p>Hello world</p><p>Foo bar</p><h2>Other</h2>')
    new = children_of('<p>Hello earth</p><p>Foo bar</p>')
    assert_equal(fuzzy_match_blocks(old, new), [(0, 0, 2), (3, 2, 0)])
