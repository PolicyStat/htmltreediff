from htmltreediff.util import (
    check_text_similarity,
    is_element,
    minidom_tostring,
    parse_minidom,
    parse_text,
    remove_node,
    unwrap,
    wrap_inner,
    wrap_nodes,
)
from htmltreediff.changes import dom_diff, distribute

import re


def diff(old_html, new_html, cutoff=0.0, plaintext=False, pretty=False):
    """Show the differences between the old and new html document, as html.

    Return the document html with extra tags added to show changes. Add <ins>
    tags around newly added sections, and <del> tags to show sections that have
    been deleted.
    """
    if plaintext:
        old_dom = parse_text(old_html)
        new_dom = parse_text(new_html)
    else:
        old_dom = parse_minidom(old_html)
        new_dom = parse_minidom(new_html)

    # If the two documents are not similar enough, don't show the changes.
    if not check_text_similarity(old_dom, new_dom, cutoff):
        return (
            '<h2>The differences from the previous version are too large to '
            'show concisely.</h2>'
        )

    dom = dom_diff(old_dom, new_dom)

    # HTML-specific cleanup.
    if not plaintext:
        fix_lists(dom)
        fix_tables(dom)
        add_class_to_empty_del_tags(dom)

    # Only return html for the document body contents.
    body_elements = dom.getElementsByTagName('body')
    if len(body_elements) == 1:
        dom = body_elements[0]

    return minidom_tostring(dom, pretty=pretty)


def _internalize_changes_markup(dom, child_tag_names):
    # Delete tags are always ordered first.
    for del_tag in list(dom.getElementsByTagName('del')):
        ins_tag = del_tag.nextSibling
        # The one child tag of `del_tag` should be child_tag_names
        if len(del_tag.childNodes) != 1:
            continue
        if ins_tag is None or len(ins_tag.childNodes) != 1:
            continue
        if ins_tag.tagName != 'ins':
            continue
        deleted_tag = del_tag.firstChild
        if not is_element(deleted_tag):
            continue
        if deleted_tag.tagName not in child_tag_names:
            continue
        # The one child tag of `ins_tag` should be child_tag_names
        inserted_tag = ins_tag.firstChild
        if not is_element(inserted_tag):
            continue
        if inserted_tag.tagName not in child_tag_names:
            continue

        attributes = dict(
            [key, value] for key, value in
            inserted_tag.attributes.items()
        )
        nodes_to_unwrap = [
            deleted_tag,
            inserted_tag,
        ]
        for n in nodes_to_unwrap:
            unwrap(n)
        new_node = wrap_nodes([del_tag, ins_tag], inserted_tag.tagName)
        for key, value in attributes.items():
            new_node.setAttribute(key, value)


def fix_lists(dom):
    # <ins> and <del> tags are not allowed within <ul> or <ol> tags.
    # Move them to the nearest li, so that the numbering isn't interrupted.

    _internalize_changes_markup(dom, set(['li']))

    # Find all del > li and ins > li sets.
    del_tags = set()
    ins_tags = set()
    for node in list(dom.getElementsByTagName('li')):
        parent = node.parentNode
        if parent.tagName == 'del':
            del_tags.add(parent)
        elif parent.tagName == 'ins':
            ins_tags.add(parent)
    # Change ins > li into li > ins.
    for ins_tag in ins_tags:
        distribute(ins_tag)
    # Change del > li into li.del-li > del.
    for del_tag in del_tags:
        children = list(del_tag.childNodes)
        unwrap(del_tag)
        for c in children:
            if c.nodeName == 'li':
                c.setAttribute('class', 'del-li')
                wrap_inner(c, 'del')


def fix_tables(dom):
    _internalize_changes_markup(dom, set(['td', 'th']))

    # Show table row insertions
    tags = set()
    for node in list(dom.getElementsByTagName('tr')):
        parent = node.parentNode
        if parent.tagName in ('ins', 'del'):
            tags.add(parent)
    for tag in tags:
        distribute(tag)
    # Show table cell insertions
    tags = set()
    for node in list(dom.getElementsByTagName('td') + dom.getElementsByTagName('th')):
        parent = node.parentNode
        if parent.tagName in ('ins', 'del'):
            tags.add(parent)
    for tag in tags:
        distribute(tag)
    # All other ins and del tags inside a table but not in a cell are invalid,
    # so remove them.
    for node in list(dom.getElementsByTagName('ins') + dom.getElementsByTagName('del')):
        parent = node.parentNode
        if parent.tagName in ['table', 'tbody', 'thead', 'tfoot', 'tr']:
            remove_node(node)


def add_class_to_empty_del_tags(dom):
    for node in dom.getElementsByTagName('del'):
        if not node.hasChildNodes():
            node.setAttribute('class', 'empty')
        else:
            all_blank = True
            for child in node.childNodes:
                if child.nodeType == node.TEXT_NODE:
                    # Confirm that the text is all whitespace
                    if not re.match('^\s*$', child.nodeValue):
                        all_blank = False
                        break
                else:
                    # will not mark del tags with child elements
                    # For future improvement: search for any nonwhitespace text
                    # or block element that is expected to be visible
                    all_blank = False
                    break
            if all_blank:
                node.setAttribute('class', 'empty')
