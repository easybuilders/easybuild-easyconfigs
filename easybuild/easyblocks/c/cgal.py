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
import os
from easybuild.easyblocks.c.cmake import CMake

class CGAL(CMake):
    def configure(self):
        """add some extra environment variables here before doing the configure"""
        os.environ['GMP_INC_DIR'] = "%s%s" % (os.environ['SOFTROOTGMP'], "/include/")
        os.environ['GMP_LIB_DIR'] = "%s%s" % (os.environ['SOFTROOTGMP'], "/lib/")
        os.environ['MPFR_INC_DIR'] = "%s%s" % (os.environ['SOFTROOTMPFR'], "/include/")
        os.environ['MPFR_LIB_DIR'] = "%s%s" % (os.environ['SOFTROOTMPFR'], "/lib/")
        os.environ['BOOST_ROOT'] = os.environ['SOFTROOTBOOST']
        CMake.configure(self)
