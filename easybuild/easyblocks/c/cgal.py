##
# Copyright 2009-2013 Ghent University
#
# This file is part of EasyBuild,
# originally created by the HPC team of Ghent University (http://ugent.be/hpc/en),
# with support of Ghent University (http://ugent.be/hpc),
# the Flemish Supercomputer Centre (VSC) (https://vscentrum.be/nl/en),
# the Hercules foundation (http://www.herculesstichting.be/in_English)
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
EasyBuild support for CGAL, implemented as an easyblock

@author: Kenneth Hoste (Ghent University)
@author: Jens Timmerman (Ghent University)
"""
import os

from easybuild.easyblocks.generic.cmakemake import CMakeMake
from easybuild.tools.modules import get_software_root


class EB_CGAL(CMakeMake):
    """Support for building CGAL."""

    def configure_step(self):
        """Set some extra environment variables before configuring."""

        deps = ["Boost", "GMP", "MPFR"]
        for dep in deps:
            if not get_software_root(dep):
                self.log.error("Dependency module %s not loaded?" % dep)

        for lib in ["GMP", "MPFR"]:
            os.environ['%s_INC_DIR' % lib] = "%s%s" % (get_software_root(lib), "/include/")
            os.environ['%s_LIB_DIR' % lib] = "%s%s" % (get_software_root(lib), "/lib/")

        os.environ['BOOST_ROOT'] = get_software_root("Boost")

        super(EB_CGAL, self).configure_step()

    def sanity_check_step(self):
        """Custom sanity check for CGAL."""

        custom_paths = {
                        'files': ['bin/cgal_%s' % x for x in ["create_cmake_script", "make_macosx_app"]] +
                                 ['lib/libCGAL%s.so' % x for x in ["", "_Core"]],
                        'dirs':['include/CGAL', 'lib/CGAL']
                       }

        super(EB_CGAL, self).sanity_check_step(custom_paths=custom_paths)
