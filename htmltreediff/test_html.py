from textwrap import dedent

from nose.tools import assert_equal

from htmltreediff.html import diff
from htmltreediff.tests import assert_html_equal
from htmltreediff.changes import distribute
from htmltreediff.html import fix_lists, fix_tables
from htmltreediff.util import (
    parse_minidom,
    minidom_tostring,
    remove_insignificant_text_nodes,
    remove_xml_declaration,
    get_location,
)
from htmltreediff.test_util import collapse


# Preprocessing

preprocessing_cases = [
    (
        'empty document',
        '',
        '',
        '<body/>'
    ),
    (
        'tail text',
        '<h1>one</h1>tail',
        '<h1>one</h1>tail',
        '<body><h1>one</h1>tail</body>',
    ),
    (
        'ignore comments',
        '<div/><!--comment one--><!--comment two-->',
        '<div/>',
        '<body><div/></body>',
    ),
    (
        'ignore style tags',
        '<style type="text/css"></style>',
        '',
        '<body/>',
    ),
    (
        'style tag in a block of text',
        '<p>xxx<style type="text/css"></style>yyy</p>',
        '<p>xxxyyy</p>',
        '<body><p>xxxyyy</p></body>',
    ),
    (
        'ignore font tags',
        '<font type="text/css"></font>',
        '',
        '<body/>',
    ),
    (
        'ignore comment tags',
        '<!-- test -->',
        '',
        '<body/>',
    ),
    (
        'illegal text nodes inside tables are not removed',
        '''
        <table>
            illegal text
            <tbody>
                <tr>
                    <td>stuff</td>
                </tr>
            </tbody>
        </table>
        ''',
        '<table> illegal text <tbody><tr><td>stuff</td></tr></tbody></table>',
        '<body><table> illegal text <tbody><tr><td>stuff</td></tr></tbody></table></body>',  # noqa
    ),
]


def test_preprocessing():
    for description, old_html, target, target_raw, in preprocessing_cases:
        def test():
            dom = parse_minidom(old_html)
            assert_equal(minidom_tostring(dom), target)
            assert_equal(remove_xml_declaration(dom.toxml()), target_raw)
        test.description = description
        yield test


def test_remove_insignificant_text_nodes():
    html = dedent('''
        <html>
            <head />
            <body>
                <p>
                    one <em>two</em> <strong>three</strong>
                </p>
                <table>
                    <tr>
                        <td>stuff</td>
                    </tr>
                </table>
            </body>
        </html>
    ''')
    target_html = ('<p> one <em>two</em> <strong>three</strong> </p> '
                   '<table><tr><td>stuff</td></tr></table>')

    dom = parse_minidom(html)
    remove_insignificant_text_nodes(dom)
    html = minidom_tostring(dom)
    assert_equal(html, target_html)

    # Check that it is idempotent.
    dom = parse_minidom(html)
    remove_insignificant_text_nodes(dom)
    html = minidom_tostring(dom)
    assert_equal(html, target_html)


def test_remove_insignificant_text_nodes_nbsp():
    html = dedent('''
        <table>
        <tbody>
        <tr>
            <td> </td>
            <td>&#160;</td>
            <td>&nbsp;</td>
            AAA
        </tr>
        </tbody>
        </table>
    ''')
    dom = parse_minidom(html)
    remove_insignificant_text_nodes(dom)
    html = minidom_tostring(dom)
    assert_equal(
        html,
        ('<table><tbody><tr><td> </td><td> </td><td> </td>'
         ' AAA </tr></tbody></table>'),
    )


# Post-processing

def test_other_node_type_inserted():
    changes = diff(
        u'<p>foo</p>',
        u'<p>foo bar</p><?xml version=\'1.0\' encoding=\'utf-8\'?>',
    )
    assert_equal(
        changes,
        '<p>foo<ins> bar</ins></p>',
    )


def test_non_printing_characters():
    changes = diff(
        '',
        '<div><p\x01>\x1Ffoo\x21</p>\x00<p>bar</p></div>',
    )
    assert_equal(
        changes,
        '<ins><div><p> foo!</p> <p>bar</p></div></ins>'
    )


def test_cutoff():
    changes = diff(
        '<h1>totally</h1>',
        '<h2>different</h2>',
        cutoff=0.2,
    )
    assert_equal(
        changes,
        '<h2>The differences from the previous version are too large to show '
        'concisely.</h2>',
    )


def test_html_diff_pretty():
    cases = [
        (
            'Simple Addition',
            '<h1>one</h1>',
            '<h1>one</h1><h2>two</h2>',
            dedent('''
                <h1>one</h1>
                <ins>
                  <h2>two</h2>
                </ins>
            ''').strip(),
        ),
    ]
    for test_name, old_html, new_html, pretty_changes in cases:
        def test():
            changes = diff(old_html, new_html, cutoff=0.0, pretty=True)
            assert_equal(pretty_changes, changes)
        test.description = 'test_html_diff_pretty - %s' % test_name
        yield test


def test_distribute():
    cases = [
        ('<ins><li>A</li><li><em>B</em></li></ins>',
         '<li><ins>A</ins></li><li><ins><em>B</em></ins></li>'),
    ]
    for original, distributed in cases:
        def test(original, distributed):
            original = parse_minidom(original)
            distributed = parse_minidom(distributed)
            node = get_location(original, [0])
            distribute(node)
            assert_html_equal(
                minidom_tostring(original),
                minidom_tostring(distributed),
            )
        yield test, original, distributed


def test_get_location():
    html = '<ins><li>A</li><li><em>B</em></li></ins>'
    original = parse_minidom(html)
    try:
        get_location(original, [10])
        raise AssertionError('ValueError not raised')
    except ValueError:
        pass


def test_fix_lists():
    cases = [
        (
            'simple list item insert',
            '''
            <ol>
              <li>one</li>
              <ins><li>two</li></ins>
            </ol>
            ''',
            '''
            <ol>
              <li>one</li>
              <li><ins>two</ins></li>
            </ol>
            '''
        ),
        (
            'multiple list item insert',
            '''
            <ol>
              <li>one</li>
              <ins>
                <li>two</li>
                <li>three</li>
              </ins>
            </ol>
            ''',
            '''
            <ol>
              <li>one</li>
              <li><ins>two</ins></li>
              <li><ins>three</ins></li>
            </ol>
            '''
        ),
        (
            'simple list item delete afterward',
            '''
            <ol>
              <li>one</li>
              <del><li>one and a half</li></del>
            </ol>
            ''',
            '''
            <ol>
              <li>one</li>
              <li class="del-li"><del>one and a half</del></li>
            </ol>
            '''
        ),
        (
            'simple list item delete first',
            '''
            <ol>
              <del><li>one half</li></del>
              <li>one</li>
            </ol>
            ''',
            '''
            <ol>
              <li class="del-li"><del>one half</del></li>
              <li>one</li>
            </ol>
            '''
        ),
        (
            'multiple list item delete first',
            '''
            <ol>
              <del>
                <li>one third</li>
                <li>two thirds</li>
              </del>
              <li>one</li>
            </ol>
            ''',
            '''
            <ol>
              <li class="del-li"><del>one third</del></li>
              <li class="del-li"><del>two thirds</del></li>
              <li>one</li>
            </ol>
            '''
        ),
        (
            'insert and delete separately',
            '''
            <ol>
              <li>one</li>
              <ins><li>two</li></ins>
              <li>three</li>
              <del><li>three point five</li></del>
              <li>four</li>
            </ol>
            ''',
            '''
            <ol>
              <li>one</li>
              <li><ins>two</ins></li>
              <li>three</del>
              <li class="del-li"><del>three point five</del></li>
              <li>four</li>
            </ol>
            '''
        ),
        (
            'multiple list item delete',
            '''
            <ol>
              <li>one</li>
              <del>
                <li>two</li>
                <li>three</li>
              </del>
            </ol>
            ''',
            '''
            <ol>
              <li>one</li>
              <li class="del-li"><del>two</del></li>
              <li class="del-li"><del>three</del></li>
            </ol>
            '''
        ),
        (
            'delete only list item',
            '''
            <ol>
              <del>
                <li>one</li>
              </del>
            </ol>
            ''',
            '''
            <ol>
              <li class="del-li"><del>one</del></li>
            </ol>
            '''
        ),
        (
            'LI full content change does not add another LI',
            '''
            <ol>
              <del>
                <li>AAA</li>
              </del>
              <ins>
                <li>BBB</li>
              </ins>
            </ol>
            ''',
            '''
            <ol>
              <li><del>AAA</del><ins>BBB</ins></li>
            </ol>
            '''
        ),
        (
            'LI full content change keeps attrs',
            '''
            <ol>
              <del>
                <li class="old" id="foo">AAA</li>
              </del>
              <ins>
                <li class="new">BBB</li>
              </ins>
            </ol>
            ''',
            '''
            <ol>
              <li class="new"><del>AAA</del><ins>BBB</ins></li>
            </ol>
            '''
        ),
        (
            'LI changes markup internalization fix not done if next tag is not an insert',  # noqa
            '''
            <ol>
              <del>
                <li>AAA</li>
              </del>
                <li><strong>BBB</strong></li>
              <ins>
                <li>CCC</li>
              </ins>
            </ol>
            ''',
            '''
            <ol>
                <li class="del-li">
                    <del>AAA</del>
                </li>
                <li><strong>BBB</strong></li>
                <li><ins>CCC</ins></li>
            </ol>
            ''',
        ),
        (
            'LI changes markup internalization fix not done if next tag is not an insert',  # noqa
            '''
            <ol>
              <del>
                <li>AAA</li>
              </del>
                <li><strong>BBB</strong></li>
              <ins>
                <li>CCC</li>
              </ins>
            </ol>
            ''',
            '''
            <ol>
                <li class="del-li">
                    <del>AAA</del>
                </li>
                <li><strong>BBB</strong></li>
                <li><ins>CCC</ins></li>
            </ol>
            ''',
        ),
        (
            'LI after del must be ins',
            '''
            <ol>
              <del>
                <li>AAA</li>
              </del>
              <del>
                <li>BBB</li>
              </del>
              <ins>
                <li>CCC</li>
              </ins>
            </ol>
            ''',
            '''
            <ol>
                <li class="del-li">
                    <del>AAA</del>
                </li>
                <li><del>BBB</del><ins>CCC</ins></li>
            </ol>
            ''',
        ),
        (
            'LI changes markup internalization fix not performed if next tags child is not li',  # noqa
            '''
            <ol>
              <del>
                <li>AAA</li>
              </del>
              <ins>
                <foo>BBB</foo>
              </ins>
            </ol>
            ''',
            '''
            <ol>
                <li class="del-li">
                    <del>AAA</del>
                </li>
                <ins>
                    <foo>BBB</foo>
                </ins>
            </ol>
            ''',
        ),
        (
            'LI changes markup internalization fix not performed if next tags is text',  # noqa
            '''
            <ol>
              <del>
                <li>AAA</li>
              </del>
              <ins>
                BBB
              </ins>
            </ol>
            ''',
            '''
            <ol>
                <li class="del-li">
                    <del>AAA</del>
                </li>
                <ins>
                    BBB
                </ins>
            </ol>
            ''',
        ),
    ]
    for test_name, changes, fixed_changes in cases:
        changes = collapse(changes)
        fixed_changes = collapse(fixed_changes)

        def test():
            changes_dom = parse_minidom(changes)
            fix_lists(changes_dom)
            assert_html_equal(minidom_tostring(changes_dom), fixed_changes)
        test.description = 'test_fix_lists - %s' % test_name
        yield test


def test_fix_tables():
    cases = [
        (
            'add a table row',
            '''
            <table>
              <tr><td>A</td></tr>
              <ins><tr><td>B</td></tr></ins>
            </table>
            ''',
            '''
            <table>
              <tr><td>A</td></tr>
              <tr><td><ins>B</ins></td></tr>
            </table>
            '''
        ),
        (
            'remove ins and del tags at the wrong level of the table',
            '''
            <table>
                <ins> </ins><del> </del>
                <thead>
                    <ins> </ins><del> </del>
                </thead>
                <tfoot>
                    <ins> </ins><del> </del>
                </tfoot>
                <tbody>
                    <ins> </ins><del> </del>
                    <tr>
                        <ins> </ins><del> </del>
                        <td><ins>A</ins></td>
                    </tr>
                </tbody>
            </table>
            ''',
            '''
            <table>
                <thead></thead>
                <tfoot></tfoot>
                <tbody>
                    <tr>
                        <td><ins>A</ins></td>
                    </tr>
                </tbody>
            </table>
            ''',
        ),
    ]
    for test_name, changes, fixed_changes in cases:
        changes = collapse(changes)
        fixed_changes = collapse(fixed_changes)

        def test():
            changes_dom = parse_minidom(changes, strict_xml=True)
            fix_tables(changes_dom)
            assert_html_equal(minidom_tostring(changes_dom), fixed_changes)
        test.description = 'test_fix_tables - %s' % test_name
        yield test
