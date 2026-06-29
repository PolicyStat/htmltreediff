import pytest

from htmltreediff.html import diff
from htmltreediff.text import split_text


@pytest.mark.parametrize('text,target', [
    ('word',
     ['word']),
    ('two words',
     ['two', ' ', 'words']),
    ('abcdef12',
     ['abcdef', '12']),
    ('entity&quot;s',
     ['entity', '&quot;', 's']),
    ('stuff&#160;stuff',
     ['stuff', '&#160;', 'stuff']),
    (
        'Stuff with an ampersand A&B stuff. Stuff with a semicolon; more stuff.',  # noqa
        [
            'Stuff', ' ', 'with', ' ', 'an', ' ', 'ampersand', ' ', 'A',
            '&', 'B', ' ', 'stuff', '.', ' ', 'Stuff', ' ', 'with', ' ',
            'a', ' ', 'semicolon', ';', ' ', 'more', ' ', 'stuff', '.',
        ],
    ),
    ("we're excited",
     ["we're", " ", "excited"]),
    ('dial 1-800-555-1234',
     ['dial', ' ', '1-800-555-1234']),
    ('Effective 1/2/2003',
     ['Effective', ' ', '1/2/2003']),
    (u'über français',
     [u'über', u' ', u'français']),
    (u'em dashes \u2013  \u2013',
     [u'em', u' ', u'dashes', u' ', u'\u2013', u'  ', u'\u2013']),
])
def test_text_split(text, target):
    assert split_text(text) == target


@pytest.mark.parametrize('description,old,new,changes', [
    (
        'sub-word changes',
        'The quick brown fox jumps over the lazy dog.',
        'The very quick brown foxes jump over the dog.',
        'The<ins> very</ins> quick brown <del>fox jumps</del><ins>foxes jump</ins> over the<del> lazy</del> dog.',  # noqa
    ),
    (
        'special characters',
        'Assume that A < B, and A & B = {}',
        'If we assume that A < B, and A & B = {}',
        '<del>Assume</del><ins>If we assume</ins> that A &lt; B, and A &amp; B = {}',  # noqa
    ),
    (
        'contractions',
        "we were excited",
        "we're excited",
        "<del>we were</del><ins>we're</ins> excited",
    ),
    (
        'dates',
        'Effective 1/2/2003',
        'Effective 3/4/2005',
        'Effective <del>1/2/2003</del><ins>3/4/2005</ins>',
    ),
    (
        'text diff with <',
        'x',
        '<',
        '<del>x</del><ins>&lt;</ins>',
    ),
    (
        'text diff with >',
        'x',
        '>',
        '<del>x</del><ins>&gt;</ins>',
    ),
    (
        'text diff with &',
        'x',
        '&',
        '<del>x</del><ins>&amp;</ins>',
    ),
    (
        'do not remove newlines unless necessary',
        'one two three\nfour six',
        'one three\nfour five six',
        'one <del>two </del>three\nfour <ins>five </ins>six',
    ),
    # long text diff is broken
    # (
    #     'long text diff',
    #     open('htmltreediff/fixtures/long_diff/before.txt').read(),
    #     open('htmltreediff/fixtures/long_diff/after.txt').read(),
    #     open('htmltreediff/fixtures/long_diff/diff.html').read(),
    # ),
], ids=lambda x: x if isinstance(x, str) else None)
def test_text_diff(description, old, new, changes):
    assert diff(old, new, plaintext=True) == changes
