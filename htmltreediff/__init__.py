from __future__ import print_function


"""
HTML Tree Diff

Basic Usage
>>> from htmltreediff import diff
>>> print(diff('<h1>...one...</h1>', '<h1>...two...</h1>', pretty=True))
<h1>
  ...
  <del>one</del>
  <ins>two</ins>
  ...
</h1>

Text Diff Usage
>>> html_diff = diff(
...     'The quick brown fox jumps over the lazy dog.',
...     'The very quick brown foxes jump over the dog.',
...     plaintext=True,
... )
>>> expected = ''.join([
...     'The<ins> very</ins> quick brown <del>fox jumps</del>',
...     '<ins>foxes jump</ins> over the<del> lazy</del> dog.',
... ])
>>> html_diff == expected
True
"""

from htmltreediff.html import diff
from htmltreediff.util import html_equal

__all__ = ['diff', 'html_equal']
