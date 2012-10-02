#!/usr/bin/env python
##
# Copyright 2009-2012 Stijn De Weirdt
# Copyright 2010 Dries Verdegem
# Copyright 2010-2012 Kenneth Hoste
# Copyright 2011 Pieter De Baets
# Copyright 2011-2012 Jens Timmerman
#
# This file is part of EasyBuild,
# originally created by the HPC team of the University of Ghent (http://ugent.be/hpc).
#
# http://github.com/hpcugent/easybuild
#
# EasyBuild is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation v2.
#
# EasyBuild is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with EasyBuild.  If not, see <http://www.gnu.org/licenses/>.
##
"""
This script creates the directory structure used by easybuild (https://github.com/easybuild/easybuild)
You can use this to set up your private repo with easyblocks and easyconfigs directories

usage: repo_setup.py

Note: you might want to put this directory under revision control.
"""

import os
import sys

def create_dir(prefix, dirname, withinit=False, init_txt=''):
    os.mkdir(os.path.join(prefix, dirname))
    if withinit:
        fh = open(os.path.join(prefix, dirname, "__init__.py"), 'w')
        fh.write(init_txt)
        fh.close()

def create_subdirs(prefix):
    # create subdirectories a, b, ..., z, 0 (catchall)
    alphabet = [chr(x) for x in xrange(ord('a'), ord('z') + 1)]
    for letter in alphabet:
        create_dir(prefix, letter)

    create_dir(prefix, "0")
    create_dir(prefix, "_generic_")

#
# MAIN
#
if len(sys.argv) > 1:
    sys.stderr.write("Usage: %s\n" % sys.argv[0])

try:
    # create root dir 'easybuild' and change into it
    dirname = "easybuild"
    os.mkdir(dirname)
    os.chdir(dirname)

    # create easyblocks dir and subdirs, with default init
    dirname = "easyblocks"
    os.mkdir(dirname)

    init_txt="""import os
from pkgutil import extend_path

# Extend path so python finds our easyblocks in the subdirectories where they are located
subdirs = [chr(l) for l in range(ord('a'),ord('z')+1)] + ['0', '_generic_']
__path__.extend([os.path.join(__path__[0], subdir) for subdir in subdirs])
# And let python know this is not the only place to look for them,
# so we can have 2 easybuild/easyblock paths in your pythonpath, one for public, one for private easyblocks.
__path__ = extend_path(__path__, __name__)
"""

    create_subdirs(dirname)

    # create easyconfigs dir and subdirs
    dirname = "easyconfigs"
    os.mkdir(dirname)
    create_subdirs(dirname)

except (IOError, OSError), err:
    sys.stderr.write("Repo setup failed: %s" % err)
    sys.exit(1)
