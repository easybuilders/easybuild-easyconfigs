##
# Copyright 2009-2016 Ghent University
# Copyright 2009-2016 Stijn De Weirdt
# Copyright 2010 Dries Verdegem
# Copyright 2010-2016 Kenneth Hoste
# Copyright 2011 Pieter De Baets
# Copyright 2011-2016 Jens Timmerman
#
# This file is part of EasyBuild,
# originally created by the HPC team of Ghent University (http://ugent.be/hpc/en),
# with support of Ghent University (http://ugent.be/hpc),
# the Flemish Supercomputer Centre (VSC) (https://vscentrum.be/nl/en),
# Flemish Research Foundation (FWO) (http://www.fwo.be/en)
# and the Department of Economy, Science and Innovation (EWI) (http://www.ewi-vlaanderen.be/en).
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
import os
import pkg_resources
import sys

# check whether EasyBuild is being run from a directory that contains easybuild/__init__.py;
# that doesn't work (fails with import errors), due to weirdness to Python packaging/setuptools/namespaces
if __path__[0] == 'easybuild':
    sys.stderr.write("ERROR: Running EasyBuild from %s does not work (Python packaging weirdness)...\n" % os.getcwd())
    sys.exit(1)

pkg_resources.declare_namespace(__name__)
