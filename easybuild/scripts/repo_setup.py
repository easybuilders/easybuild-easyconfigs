#!/usr/bin/env python
##
# Copyright 2009-2012 Stijn Deweirdt, Dries Verdegem, Kenneth Hoste, Pieter De Baets, Jens Timmerman
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

you might want to put this directory under revision control
"""

import os
import sys

def create_dir(prefix, dirname, withinit=False):
    os.mkdir(os.path.join(prefix, dirname))
    if withinit:
        fh = open(os.path.join(prefix, dirname, "__init__.py"), 'w')
        fh.close()

def create_subdirs(prefix, withinit=False):
    # create subdirectories a, b, ..., z, 0 (catchall)
    alphabet = [chr(x) for x in xrange(ord('a'), ord('z') + 1)]
    for letter in alphabet:
        create_dir(prefix, letter, withinit=withinit)

    create_dir(prefix, "0", withinit=withinit)

#
# MAIN
#
if len(sys.argv) > 1:
    sys.stderr.write("Usage: %s\n" % sys.argv[0])

# create easyblocks dir and subdirs, with default init
dirname = "easyblocks"
os.mkdir(dirname)
f = open(os.path.join(dirname, "__init__.py"), 'w')
f.write("""
from pkgutil import extend_path
__path__ = extend_path(__path__, __name__)
""" % os.path.basename(dirname))

create_subdirs(dirname, withinit=True)

# create easyconfigs dir and subdirs
dirname = "easyconfigs"
os.mkdir(dirname)
create_subdirs(dirname)
