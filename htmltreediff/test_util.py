from htmltreediff.diff_core import Differ
from htmltreediff.edit_script_runner import EditScriptRunner
from htmltreediff.changes import (
    split_text_nodes,
    sort_nodes,
)
from htmltreediff.util import (
    attribute_dict,
    minidom_tostring,
    node_compare,
    parse_minidom,
    remove_node,
    unwrap,
    walk_dom,
)


def reverse_edit_script(edit_script):
    if edit_script is None:
        return None
    opposite_command = {
        'insert': 'delete',
        'delete': 'insert',
    }
    reverse_script = []
    for action, location, node_properties in reversed(edit_script):
        reverse_script.append(
            (opposite_command[action], location, node_properties),
        )
    return reverse_script


def reverse_changes_html(changes):
    dom = parse_minidom(changes)
    reverse_changes(dom)
    return minidom_tostring(dom)


def reverse_changes(dom):
    nodes = dom.getElementsByTagName('del') + dom.getElementsByTagName('ins')
    for node in nodes:
        if node.tagName == 'del':
            node.tagName = 'ins'
        elif node.tagName == 'ins':
            node.tagName = 'del'
    sort_nodes(dom)


def get_edit_script(old_html, new_html):
    old_dom = parse_minidom(old_html)
    new_dom = parse_minidom(new_html)
    split_text_nodes(old_dom)
    split_text_nodes(new_dom)
    differ = Differ(old_dom, new_dom)
    return differ.get_edit_script()


def html_patch(old_html, edit_script):
    old_dom = parse_minidom(old_html)
    split_text_nodes(old_dom)
    runner = EditScriptRunner(old_dom, edit_script)
    return minidom_tostring(runner.run_edit_script())


def _strip_changes_new(node):
    for ins_node in node.getElementsByTagName('ins'):
        unwrap(ins_node)
    for del_node in node.getElementsByTagName('del'):
        remove_node(del_node)


def _strip_changes_old(node):
    for ins_node in node.getElementsByTagName('ins'):
        remove_node(ins_node)
    for del_node in node.getElementsByTagName('del'):
        unwrap(del_node)


def strip_changes_old(html):
    dom = parse_minidom(html)
    _strip_changes_old(dom)
    return minidom_tostring(dom)


def strip_changes_new(html):
    dom = parse_minidom(html)
    _strip_changes_new(dom)
    return minidom_tostring(dom)


def remove_dom_attributes(dom):
    for node in walk_dom(dom):
        for key in attribute_dict(node).keys():
            node.attributes.removeNamedItem(key)


def remove_attributes(html):
    dom = parse_minidom(html)
    remove_dom_attributes(dom)
    return minidom_tostring(dom)


def collapse(html):
    """Remove any indentation and newlines from the html."""
    return ''.join([line.strip() for line in html.split('\n')]).strip()


class Case(object):
    pass


def parse_cases(cases):
    for args in cases:
        case = Case()
        if len(args) == 4:
            case.name, case.old_html, case.new_html, case.target_changes = args
            case.edit_script = None
        elif len(args) == 5:
            (
                case.name,
                case.old_html,
                case.new_html,
                case.target_changes,
                case.edit_script,
            ) = args
        else:
            raise ValueError('Invalid test spec: %r' % (args,))
        yield case


def test_node_compare():
    del_node = list(walk_dom(parse_minidom('<del/>')))[-1]
    ins_node = list(walk_dom(parse_minidom('<ins/>')))[-1]
    assert -1 == node_compare(del_node, ins_node)
    assert 1 == node_compare(ins_node, del_node)
