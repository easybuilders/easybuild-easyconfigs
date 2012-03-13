"""
This script creates the directory structure used by easybuild (https://github.com/easybuild/easybuild)
You can use this to set up your private easyblocks directory

usage: easyblockssetup.py [easyblocks_privatename]

you might want to put this directory under revision control
"""

import os
import sys

if len(sys.argv) > 2:
    sys.stderr.write("Usage: %s [prefix]\n" % sys.argv[0])

PREFIX = "easyblocks"
if len(sys.argv) == 2:
    PREFIX = sys.argv[1]

# create root dir, with default init
os.mkdir(PREFIX)
f = open(os.path.join(PREFIX, "__init__.py"), 'w')
f.write("""import pkg_resources
pkg_resources.declare_namespace("%s")
""" % os.path.basename(PREFIX))

# create subdirectories Aa, Bb, ..., Zz, 09, _-
def createDir(dirName):
    os.mkdir(os.path.join(PREFIX, dirName))
    fh = open(os.path.join(PREFIX, dirName, "__init__.py"), 'w')
    fh.close()

alphabet = [chr(x) for x in xrange(ord('a'), ord('z') + 1)]
for letter in alphabet:
    dr = "%s%s" % (letter.upper(), letter)
    createDir(dr)

createDir("09")
createDir("_-")
