import sys
import tempfile
from io import StringIO
from textwrap import dedent

from htmltreediff.cli import main


def test_main():
    # Run the command line interface main function.
    f1 = tempfile.NamedTemporaryFile()
    f1.write('<h1>one</h1>'.encode('utf-8'))
    f1.seek(0)
    f2 = tempfile.NamedTemporaryFile()
    f2.write('<h1>one</h1><h2>two</h2>'.encode('utf-8'))
    f2.seek(0)

    old_stdout = sys.stdout
    try:
        sys.stdout = stream = StringIO()
        main(argv=('', f1.name, f2.name))
        expected = dedent('''
            <h1>one</h1>
            <ins>
              <h2>two</h2>
            </ins>
        ''').strip() + '\n'
        assert stream.getvalue() == expected
    finally:
        sys.stdout = old_stdout
