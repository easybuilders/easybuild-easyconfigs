"""
This script creates the directory structure used by easybuild (https://github.com/easybuild/easybuild)
You can use this to set up your private easyblocks directory

usage: easyblockssetup.py [easyblocks_privatename]

you might want to put this directory under revision control
"""

import os
import sys
PREFIX="easyblocks"
if len(sys.argv) > 1:
    PREFIX = sys.argv[1]

os.mkdir(PREFIX)
f=open(os.path.join(PREFIX,"__init__.py"),'w')
f.write("""import pkg_resources
pkg_resources.declare_namespace("%s")
"""%PREFIX)

def createdir(dr):
    os.mkdir(os.path.join(PREFIX,dr))
    f = open(os.path.join(PREFIX,dr,"__init__.py"),'w')
    f.close()

for i in xrange(ord('a'),ord('z')):
    dr = "%s%s"%( chr(ord('A')-ord('a')+i),chr(i))
    createdir(dr)

createdir("09")
createdir("_-")

   
