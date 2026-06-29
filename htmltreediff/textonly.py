"""
Text-only diff: compare two HTML documents by text content only,
ignoring structural (block-level tag) changes.

Instead of tree-diffing the DOM, this extracts "text blocks" from each
document, flattens them to word sequences, diffs the words, then renders
the word-level diff back into the new document's block structure.
"""
import difflib

from htmltreediff.text import split_text, is_text_junk, WordMatcher
from htmltreediff.util import (
    BLOCK_TAGS,
    copy_dom,
    is_element,
    is_text,
    minidom_tostring,
    parse_minidom,
    walk_dom,
)


def _is_block(node):
    """Check if a node is a block-level element."""
    return is_element(node) and node.nodeName.lower() in BLOCK_TAGS


def _extract_text_from_node(node):
    """Extract text content from a single node (recursively, inline only)."""
    if is_text(node):
        return node.nodeValue
    parts = []
    for child in node.childNodes:
        parts.append(_extract_text_from_node(child))
    return ''.join(parts)


def extract_text_blocks(dom):
    """Extract a flat list of text blocks from a DOM.

    Walk the DOM depth-first. Each time we encounter a block-level
    boundary, we emit the accumulated text as a block. Returns a list
    of (text, node) tuples where node is the block-level element that
    contains the text.
    """
    blocks = []

    def _walk_block(node):
        """Walk a block-level node, extracting text from its inline content
        and recursing into child blocks."""
        inline_text_parts = []

        for child in node.childNodes:
            if is_text(child):
                inline_text_parts.append(child.nodeValue)
            elif is_element(child):
                if _is_block(child):
                    # Flush any accumulated inline text before this block
                    text = ''.join(inline_text_parts).strip()
                    if text:
                        blocks.append((text, node))
                        inline_text_parts.clear()
                    # Recurse into the child block
                    _walk_block(child)
                else:
                    # Inline element - extract text recursively
                    inline_text_parts.append(
                        _extract_text_from_node(child)
                    )

        # Flush remaining inline text
        text = ''.join(inline_text_parts).strip()
        if text:
            blocks.append((text, node))

    body = dom.documentElement
    _walk_block(body)
    return blocks


def _blocks_to_words(blocks):
    """Convert blocks to a flat word list with block boundary markers.

    Returns:
        words: list of word strings
        block_map: list of (block_index, word_offset_within_block) for each word
    """
    words = []
    block_map = []
    for block_idx, (text, _node) in enumerate(blocks):
        block_words = split_text(text)
        for word_offset, word in enumerate(block_words):
            words.append(word)
            block_map.append((block_idx, word_offset))
    return words, block_map


def _word_diff_to_block_diffs(opcodes, old_words, new_words,
                              new_block_map, new_blocks):
    """Convert word-level opcodes into per-block diff annotations.

    For each new block, produce the HTML content showing what changed
    relative to the old document. Returns a tuple of:
        - block_diffs: {new_block_index: diff_html_string} for blocks with
          inline changes
        - deleted_before: {new_block_index: [deleted_text, ...]} for content
          that was deleted and should appear as standalone del blocks

    Blocks that have no changes are not included in the result.
    """
    # Accumulate diff pieces per new block
    block_pieces = {}  # block_idx -> list of html parts in order
    # Track deleted content that should render as standalone del blocks
    deleted_before = {}  # block_idx -> list of deleted text strings

    for tag, i1, i2, j1, j2 in opcodes:
        if tag == 'equal':
            # These words exist unchanged in the new doc
            for j in range(j1, j2):
                block_idx = new_block_map[j][0]
                if block_idx not in block_pieces:
                    block_pieces[block_idx] = []
                block_pieces[block_idx].append(new_words[j])
        elif tag == 'replace':
            # Old words replaced with new words
            if j1 < j2:
                block_idx = new_block_map[j1][0]
                if block_idx not in block_pieces:
                    block_pieces[block_idx] = []
                del_text = ''.join(old_words[i1:i2])
                block_pieces[block_idx].append('<del>%s</del>' % del_text)
                for j in range(j1, j2):
                    b_idx = new_block_map[j][0]
                    if b_idx != block_idx:
                        if b_idx not in block_pieces:
                            block_pieces[b_idx] = []
                        block_pieces[b_idx].append(
                            '<ins>%s</ins>' % new_words[j]
                        )
                    else:
                        block_pieces[block_idx].append(
                            '<ins>%s</ins>' % new_words[j]
                        )
        elif tag == 'delete':
            # Words in old but not in new.
            # Determine where to show the deletion based on context:
            # If the deletion is between matched content within the same new
            # block (preceded AND followed by equal content in that block),
            # show it inline. Otherwise show as a standalone deleted block.
            if j1 < len(new_block_map):
                block_idx = new_block_map[j1][0]
            elif j1 > 0 and new_block_map:
                block_idx = new_block_map[j1 - 1][0]
            elif new_block_map:
                block_idx = new_block_map[0][0]
            else:
                continue

            # Check if there's preceding equal/matched content in same block
            has_preceding = (
                j1 > 0 and j1 - 1 < len(new_block_map) and
                new_block_map[j1 - 1][0] == block_idx
            )

            del_text = ''.join(old_words[i1:i2])

            if has_preceding:
                # Inline deletion within a block (between matched words)
                if block_idx not in block_pieces:
                    block_pieces[block_idx] = []
                block_pieces[block_idx].append('<del>%s</del>' % del_text)
            else:
                # Standalone deleted block (content removed before this block)
                if block_idx not in deleted_before:
                    deleted_before[block_idx] = []
                deleted_before[block_idx].append(del_text)
        elif tag == 'insert':
            # Words in new but not in old
            for j in range(j1, j2):
                block_idx = new_block_map[j][0]
                if block_idx not in block_pieces:
                    block_pieces[block_idx] = []
                block_pieces[block_idx].append(
                    '<ins>%s</ins>' % new_words[j]
                )

    # Determine which blocks have inline changes
    import re
    block_diffs = {}
    for block_idx in block_pieces:
        pieces = block_pieces[block_idx]
        html = ''.join(pieces)
        original_text = new_blocks[block_idx][0]
        # Filter out whitespace-only del/ins tags (artifacts of block
        # boundary differences)
        cleaned = re.sub(r'<(ins|del)>\s*</\1>', '', html)
        if cleaned != original_text:
            block_diffs[block_idx] = cleaned

    # Filter out whitespace-only deleted blocks
    for block_idx in list(deleted_before.keys()):
        deleted_before[block_idx] = [
            t for t in deleted_before[block_idx] if t.strip()
        ]
        if not deleted_before[block_idx]:
            del deleted_before[block_idx]

    return block_diffs, deleted_before


def _rebuild_node_with_diff(node, diff_html):
    """Replace the inline text content of a block node with diff markup."""
    doc = node.ownerDocument

    # Clear existing children
    while node.hasChildNodes():
        node.removeChild(node.firstChild)

    # Parse the diff html as a fragment and import nodes
    from htmltreediff.util import parse_lxml_dom
    fragment_dom = parse_lxml_dom(
        '<body>%s</body>' % diff_html, strict_xml=False
    )
    body_elements = fragment_dom.getElementsByTagName('body')
    if body_elements:
        fragment_body = body_elements[0]
    else:
        fragment_body = fragment_dom.documentElement

    for child in list(fragment_body.childNodes):
        imported = doc.importNode(child, deep=True)
        node.appendChild(imported)


def textonly_diff(old_html, new_html, cutoff=0.0, pretty=False):
    """Diff two HTML documents showing only text content changes.

    The output uses the new document's HTML structure, with <ins> and <del>
    tags showing word-level text changes. Structural changes (e.g. <p> to
    <h2>) are invisible in this diff.
    """
    old_dom = parse_minidom(old_html)
    new_dom = parse_minidom(new_html)

    # Extract text blocks
    old_blocks = extract_text_blocks(old_dom)
    new_blocks = extract_text_blocks(new_dom)

    if not old_blocks and not new_blocks:
        return minidom_tostring(new_dom, pretty=pretty)

    # Flatten blocks to word sequences
    old_words, _old_block_map = _blocks_to_words(old_blocks)
    new_words, new_block_map = _blocks_to_words(new_blocks)

    # Check overall similarity
    sm = WordMatcher(a=old_words, b=new_words)
    if cutoff > 0 and sm.text_ratio() < cutoff:
        return (
            '<h2>The differences from the previous version are too large to '
            'show concisely.</h2>'
        )

    # Word-level diff across the entire flattened text
    word_sm = difflib.SequenceMatcher(is_text_junk, old_words, new_words)
    opcodes = word_sm.get_opcodes()

    # Convert word opcodes to per-block diff annotations
    block_diffs, deleted_before = _word_diff_to_block_diffs(
        opcodes, old_words, new_words, new_block_map, new_blocks
    )

    # If no changes at all, return the new doc as-is
    if not block_diffs and not deleted_before:
        result_dom = copy_dom(new_dom)
        return minidom_tostring(result_dom, pretty=pretty)

    # Build output by modifying a copy of the new DOM
    result_dom = copy_dom(new_dom)
    result_blocks = extract_text_blocks(result_dom)
    body = result_dom.documentElement
    doc = result_dom

    # Apply word-diff annotations to modified blocks
    for block_idx, diff_html in block_diffs.items():
        if block_idx < len(result_blocks):
            node = result_blocks[block_idx][1]
            _rebuild_node_with_diff(node, diff_html)

    # Insert standalone deleted block markers before their reference blocks
    for target_idx in sorted(deleted_before.keys(), reverse=True):
        texts = deleted_before[target_idx]
        if target_idx < len(result_blocks):
            ref_node = result_blocks[target_idx][1]
            parent = ref_node.parentNode
            for text in reversed(texts):
                del_node = doc.createElement('del')
                del_node.setAttribute('class', 'block-deleted')
                text_node = doc.createTextNode(text)
                del_node.appendChild(text_node)
                parent.insertBefore(del_node, ref_node)
        else:
            # Append at end of body
            for text in texts:
                del_node = doc.createElement('del')
                del_node.setAttribute('class', 'block-deleted')
                text_node = doc.createTextNode(text)
                del_node.appendChild(text_node)
                body.appendChild(del_node)

    return minidom_tostring(result_dom, pretty=pretty)

