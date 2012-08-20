##
# Copyright 2012 Kenneth Hoste
# Copyright 2012 Jens Timmerman
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
EasyBuild support for CGAL, implemented as an easyblock
"""
import os

from easybuild.easyblocks.c.cmake import EB_CMake
from easybuild.tools.modules import get_software_root


class EB_CGAL(EB_CMake):
    """Support for building CGAL."""

    def configure(self):
        """Set some extra environment variables before configuring."""

        deps = ["Boost", "GMP", "MPFR"]
        for dep in deps:
            if not get_software_root(dep):
                self.log.error("Dependency module %s not loaded?" % dep)

        for lib in ["GMP", "MPFR"]:
            os.environ['%s_INC_DIR' % lib] = "%s%s" % (get_software_root(lib), "/include/")
            os.environ['%s_LIB_DIR' % lib] = "%s%s" % (get_software_root(lib), "/lib/")

        os.environ['BOOST_ROOT'] = get_software_root("Boost")

        EB_CMake.configure(self)

    def sanitycheck(self):
        """Custom sanity check for CGAL."""

        if not self.getcfg('sanityCheckPaths'):

            self.setcfg('sanityCheckPaths', {
                                             'files': ['bin/cgal_%s' % x for x in ["create_cmake_script",
                                                                                   "make_macosx_app"]] +
                                                      ['lib/libCGAL%s.so' % x for x in ["", "_Core"]],
                                             'dirs':['include/CGAL', 'lib/CGAL']
                                             })

            self.log.info("Customized sanity check paths: %s" % self.getcfg('sanityCheckPaths'))

        EB_CMake.sanitycheck(self)
