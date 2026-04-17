import difflib
from xml.dom import Node

import six

from htmltreediff.text import is_text_junk
from htmltreediff.util import (
    copy_dom,
    HashableTree,
    FuzzyHashableTree,
    is_text,
    get_child,
    get_location,
    remove_node,
    insert_or_append,
    attribute_dict,
    walk_dom,
)


def match_node_hash(node):
    if is_text(node):
        return node.nodeValue
    return HashableTree(node)


def fuzzy_match_node_hash(node):
    if is_text(node):
        return node.nodeValue
    return FuzzyHashableTree(node)


class Differ():
    def __init__(self, old_dom, new_dom):
        self.edit_script = []
        self.old_dom = copy_dom(old_dom)
        self.new_dom = copy_dom(new_dom)

    def get_edit_script(self):
        """
        Take two doms, and output an edit script transforming one into the
        other.

        edit script output format
        Actions:
        - ('delete', location, node_properties)
            delete the node, and all descendants
        - ('insert', location, node_properties)
            insert the node at the given location, with the given properties
        The location argument is a tuple of indices.
        The node properties is a dictionary possibly containing keys:
            {node_type, tag_name, attributes, node_value.}
        Any properties that would be empty may be ommitted. attributes is an
        attribute dictionary.
        """
        # start diff at the body element
        self.diff_location([], [])
        return self.edit_script

    def diff_location(self, old_location, new_location):
        # Here we match up the children of the given locations. This is done in
        # three steps. First we use full tree equality to match up children
        # that are identical all the way down. Then, we use a heuristic
        # function to match up children that are similar, based on text
        # content. Lastly, we just use node tag types to match up elements. For
        # the text-similar matches and the tag-only matches, we still have more
        # work to do, so we recurse on these. The non-matching parts that
        # remain are used to output edit script entries.
        old_children = list(
            get_location(self.old_dom, old_location).childNodes,
        )
        new_children = list(
            get_location(self.new_dom, new_location).childNodes,
        )
        if not old_children and not new_children:
            return

        matching_blocks, recursion_indices = self.match_children(
            old_children,
            new_children,
        )

        # Apply changes for this level.
        for tag, i1, i2, j1, j2 in adjusted_ops(get_opcodes(matching_blocks)):
            if tag == 'delete':
                assert j1 == j2
                # delete range from right to left
                children = reversed(list(enumerate(old_children[i1:i2])))
                for index, child in children:
                    self.delete(old_location + [i1 + index], child)
                    old_children.pop(i1 + index)
            elif tag == 'insert':
                assert i1 == i2
                # insert range from left to right
                for index, child in enumerate(new_children[j1:j2]):
                    self.insert(new_location + [i1 + index], child)
                    old_children.insert(i1 + index, child)
            recursion_indices = list(
                adjust_indices(recursion_indices, i1, i2, j1, j2),
            )

        # Recurse to deeper level.
        for old_index, new_index in recursion_indices:
            self.diff_location(
                old_location + [old_index],
                new_location + [new_index],
            )

    def match_children(self, old_children, new_children):
        # Find whole-tree matches and fuzzy matches.
        sm = match_blocks(match_node_hash, old_children, new_children)
        # If the match is very poor, pretend there were no exact matching
        # blocks at all.
        if sm.ratio() < 0.3:
            matching_blocks = [(len(old_children), len(new_children), 0)]
        else:
            matching_blocks = sm.get_matching_blocks()

        # In each gap between exact matches, find fuzzy matches.
        gaps = get_nonmatching_blocks(matching_blocks)

        fuzzy_matching_blocks = [(0, 0, 0)]
        for nonmatch in gaps:
            alo, ahi, blo, bhi = nonmatch
            gap_old = old_children[alo:ahi]
            gap_new = new_children[blo:bhi]
            if _has_fuzzy_hash_collisions(gap_new):
                blocks = fuzzy_match_blocks(gap_old, gap_new)
            else:
                sm_fuzzy = match_blocks(
                    fuzzy_match_node_hash,
                    gap_old,
                    gap_new,
                )
                blocks = sm_fuzzy.get_matching_blocks()
            # Move blocks over to the position of the gap.
            blocks = [
                (alo + a, blo + b, size)
                for a, b, size in blocks
            ]
            del fuzzy_matching_blocks[-1]  # Remove old sentinel.
            fuzzy_matching_blocks.extend(blocks)

        # We will recurse on each tree that was a fuzzy match at this level.
        recursion_indices = []  # List of tuples, (old_index, new_index)
        for match in fuzzy_matching_blocks:
            for old_index, new_index in match_indices(match):
                recursion_indices.append((old_index, new_index))

        # Zip together the fuzzy and exact matches. They are treated the same
        # from this point forward, except for we recurse on fuzzy matches.
        matching_blocks = merge_blocks(matching_blocks, fuzzy_matching_blocks)

        return matching_blocks, recursion_indices

    def delete(self, location, node):
        # delete from the bottom up, children before parent, right to left
        for child_index, child in reversed(list(enumerate(node.childNodes))):
            self.delete(location + [child_index], child)
        # write deletion to the edit script
        self.edit_script.append((
            'delete',
            location,
            node_properties(node),
        ))
        # actually delete the node
        assert node.parentNode == get_location(self.old_dom, location[:-1])
        assert node.ownerDocument == self.old_dom
        remove_node(node)

    def insert(self, location, node):
        # write insertion to the edit script
        self.edit_script.append((
            'insert',
            location,
            node_properties(node),
        ))
        # actually insert the node
        node_copy = node.cloneNode(deep=False)
        parent = get_location(self.old_dom, location[:-1])
        next_sibling = get_child(parent, location[-1])
        insert_or_append(parent, node_copy, next_sibling)
        # insert from the top down, parent before children, left to right
        for child_index, child in enumerate(node.childNodes):
            self.insert(location + [child_index], child)


def adjusted_ops(opcodes):
    """
    Iterate through opcodes, turning them into a series of insert and delete
    operations, adjusting indices to account for the size of insertions and
    deletions.

    >>> def sequence_opcodes(old, new):
    ...     return difflib.SequenceMatcher(a=old, b=new).get_opcodes()
    >>> list(adjusted_ops(sequence_opcodes('abc', 'b')))
    [('delete', 0, 1, 0, 0), ('delete', 1, 2, 1, 1)]
    >>> list(adjusted_ops(sequence_opcodes('b', 'abc')))
    [('insert', 0, 0, 0, 1), ('insert', 2, 2, 2, 3)]
    >>> list(adjusted_ops(sequence_opcodes('axxa', 'aya')))
    [('delete', 1, 3, 1, 1), ('insert', 1, 1, 1, 2)]
    >>> list(adjusted_ops(sequence_opcodes('axa', 'aya')))
    [('delete', 1, 2, 1, 1), ('insert', 1, 1, 1, 2)]
    >>> list(adjusted_ops(sequence_opcodes('ab', 'bc')))
    [('delete', 0, 1, 0, 0), ('insert', 1, 1, 1, 2)]
    >>> list(adjusted_ops(sequence_opcodes('bc', 'ab')))
    [('insert', 0, 0, 0, 1), ('delete', 2, 3, 2, 2)]
    """
    while opcodes:
        op = opcodes.pop(0)
        tag, i1, i2, j1, j2 = op
        shift = 0
        if tag == 'equal':
            continue
        if tag == 'replace':
            # change the single replace op into a delete then insert
            # pay careful attention to the variables here, there's no typo
            opcodes = [
                ('delete', i1, i2, j1, j1),
                ('insert', i2, i2, j1, j2),
            ] + opcodes
            continue
        yield op
        if tag == 'delete':
            shift = -(i2 - i1)
        elif tag == 'insert':
            shift = +(j2 - j1)
        new_opcodes = []
        for tag, i1, i2, j1, j2 in opcodes:
            new_opcodes.append((
                tag,
                i1 + shift,
                i2 + shift,
                j1,
                j2,
            ))
        opcodes = new_opcodes


def node_properties(node):
    d = {}
    d['node_type'] = node.nodeType
    d['node_name'] = node.nodeName
    d['node_value'] = node.nodeValue
    d['attributes'] = attribute_dict(node)
    if node.nodeType == Node.TEXT_NODE:
        del d['node_name']  # don't include node name for text nodes
    for key, value in list(d.items()):
        if not value:
            del d[key]
    return d


def match_indices(match):
    """
    Yield index tuples (old_index, new_index) for each place in the match.
    """
    a, b, size = match
    for i in range(size):
        yield a + i, b + i


def get_opcodes(matching_blocks):
    """Use difflib to get the opcodes for a set of matching blocks."""
    sm = difflib.SequenceMatcher(a=[], b=[])
    sm.matching_blocks = matching_blocks
    return sm.get_opcodes()


def _is_junk(hashable_node):
    if isinstance(hashable_node, six.string_types):
        return is_text_junk(hashable_node)
    # Nodes with no text or just whitespace are junk.
    for descendant in walk_dom(hashable_node.node):
        if is_text(descendant):
            if not is_text_junk(descendant.nodeValue):
                return False
    return True


def match_blocks(hash_func, old_children, new_children):
    """Use difflib to find matching blocks."""
    sm = difflib.SequenceMatcher(
        _is_junk,
        a=[hash_func(c) for c in old_children],
        b=[hash_func(c) for c in new_children],
    )
    return sm


def _has_fuzzy_hash_collisions(children):
    """Check if element children have hash collisions in fuzzy matching.

    When multiple element nodes hash to the same FuzzyHashableTree value,
    SequenceMatcher may group them incorrectly due to non-transitive equality,
    causing misaligned matches. Text nodes use string equality (which is
    transitive) and are not affected.
    """
    seen_hashes = set()
    for c in children:
        if is_text(c):
            continue
        h = hash(fuzzy_match_node_hash(c))
        if h in seen_hashes:
            return True
        seen_hashes.add(h)
    return False


def build_pairwise_match_matrix(old_hashes, new_hashes):
    n = len(old_hashes)
    m = len(new_hashes)
    match_matrix = [[False] * m for _ in range(n)]
    for i in range(n):
        for j in range(m):
            match_matrix[i][j] = (old_hashes[i] == new_hashes[j])
    return match_matrix


def compute_longest_common_subsequence_lengths_table(match_matrix):
    n = len(match_matrix)
    m = len(match_matrix[0]) if n > 0 else 0
    lcs_lengths = [[0] * (m + 1) for _ in range(n + 1)]
    for i in reversed(range(n)):
        for j in reversed(range(m)):
            if match_matrix[i][j]:
                lcs_lengths[i][j] = 1 + lcs_lengths[i + 1][j + 1]
            else:
                lcs_lengths[i][j] = max(lcs_lengths[i + 1][j], lcs_lengths[i][j + 1])
    return lcs_lengths


def traceback_longest_common_subsequence_matched_pairs(match_matrix, lcs_lengths):
    n = len(match_matrix)
    m = len(match_matrix[0]) if n > 0 else 0
    matched_pairs = []
    i, j = 0, 0
    while i < n and j < m:
        if match_matrix[i][j] and lcs_lengths[i][j] == 1 + lcs_lengths[i + 1][j + 1]:
            matched_pairs.append((i, j))
            i += 1
            j += 1
        elif lcs_lengths[i + 1][j] >= lcs_lengths[i][j + 1]:
            i += 1
        else:
            j += 1
    return matched_pairs


def group_consecutive_pairs_into_blocks(matched_pairs, n, m):
    blocks = []
    k = 0
    while k < len(matched_pairs):
        a, b = matched_pairs[k]
        size = 1
        while (
            k + size < len(matched_pairs) and matched_pairs[k + size] == (a + size, b + size)
        ):
            size += 1
        blocks.append((a, b, size))
        k += size
    blocks.append((n, m, 0))  # sentinel
    return blocks


def fuzzy_match_blocks(old_children, new_children):
    """Find matching blocks using direct pairwise fuzzy comparison.

    Unlike match_blocks (which uses SequenceMatcher), this compares each
    old-new pair individually using FuzzyHashableTree. This avoids
    misalignment caused by FuzzyHashableTree's non-transitive equality:
    SequenceMatcher groups elements into a dict by equality, so when A==B and
    B==C but A!=C, elements get merged into incorrect groups and the longest
    common subsequence is computed on wrong groupings.

    Explaination: https://www.geeksforgeeks.org/dsa/longest-common-subsequence-dp-4/#expected-approach-1-using-bottomup-dp-tabulation-om-n-time-and-om-n-space
    """
    n = len(old_children)
    m = len(new_children)

    if n == 0 or m == 0:
        return [(n, m, 0)]

    old_hashes = [fuzzy_match_node_hash(c) for c in old_children]
    new_hashes = [fuzzy_match_node_hash(c) for c in new_children]

    match_matrix = build_pairwise_match_matrix(old_hashes, new_hashes)
    lcs_lengths = compute_longest_common_subsequence_lengths_table(match_matrix)
    matched_pairs = traceback_longest_common_subsequence_matched_pairs(
        match_matrix,
        lcs_lengths,
    )
    return group_consecutive_pairs_into_blocks(matched_pairs, n, m)


def get_nonmatching_blocks(matching_blocks):
    """Given a list of matching blocks, output the gaps between them.

    Non-matches have the format (alo, ahi, blo, bhi). This specifies two index
    ranges, one in the A sequence, and one in the B sequence.
    """
    i = j = 0
    for match in matching_blocks:
        a, b, size = match
        yield (i, a, j, b)
        i = a + size
        j = b + size


def merge_blocks(a_blocks, b_blocks):
    """Given two lists of blocks, combine them, in the proper order.

    Ensure that there are no overlaps, and that they are for sequences of the
    same length.
    """
    # Check sentinels for sequence length.
    assert a_blocks[-1][2] == b_blocks[-1][2] == 0  # sentinel size is 0
    assert a_blocks[-1] == b_blocks[-1]
    combined_blocks = sorted(list(set(a_blocks + b_blocks)))
    # Check for overlaps.
    i = j = 0
    for a, b, size in combined_blocks:
        assert i <= a
        assert j <= b
        i = a + size
        j = b + size
    return combined_blocks


def adjust_indices(indices, i1, i2, j1, j2):
    shift = (j2 - j1) - (i2 - i1)
    for a, b in indices:
        if a >= i2:
            a += shift
        yield a, b
