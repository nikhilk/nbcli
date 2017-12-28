# __init__.py
# Declares the Sample CLI for use in a notebook kernel.

import nbcli
import _hello as hello
import _foo as foo

nbcli.create('sample', [hello, foo])

