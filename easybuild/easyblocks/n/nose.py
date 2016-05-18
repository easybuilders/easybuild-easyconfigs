##
# Copyright 2009-2016 Ghent University
#
# This file is part of EasyBuild,
# originally created by the HPC team of Ghent University (http://ugent.be/hpc/en),
# with support of Ghent University (http://ugent.be/hpc),
# the Flemish Supercomputer Centre (VSC) (https://www.vscentrum.be),
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
"""
EasyBuild support for building and installing nose, implemented as an easyblock

@author: Stijn De Weirdt (Ghent University)
@author: Dries Verdegem (Ghent University)
@author: Kenneth Hoste (Ghent University)
@author: Pieter De Baets (Ghent University)
@author: Jens Timmerman (Ghent University)
"""
from easybuild.easyblocks.generic.pythonpackage import PythonPackage


class EB_nose(PythonPackage):
    """Support for installing the nose Python package as part of a Python installation."""

    def __init__(self, *args, **kwargs):
        """Set custom class variables (unpack options)."""
        super(EB_nose, self).__init__(*args, **kwargs)

        # use extra unpack options to avoid problems like
        # 'tar: Ignoring unknown extended header keyword `SCHILY.nlink'
        # and tar exiting with non-zero exit code
        self.unpack_options = ' --pax-option="delete=SCHILY.*" --pax-option="delete=LIBARCHIVE.*" '
