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
EasyBuild support for installing the Intel Fortran compiler suite, implemented as an easyblock
"""

from distutils.version import LooseVersion

from easybuild.easyblocks.i.icc import Icc, IntelBase


class eb_ifort(Icc):
    """
    Class that can be used to install ifort
    - tested with 11.1.046
    -- will fail for all older versions (due to newer silent installer)
    """

    def sanitycheck(self):

        if not self.getcfg('sanityCheckPaths'):

            libprefix = ""
            if LooseVersion(self.version()) >= LooseVersion("2011"):
                libprefix = "compiler/lib/intel64/lib"
            else:
                libprefix = "lib/intel64/lib"

            self.setcfg('sanityCheckPaths', {
                                             'files': ["bin/intel64/%s" % x for x in ["ifort", "idb"]] +
                                                      ["%s%s" % (libprefix, x) for x in ["ifcore.a", "ifcore.so",
                                                                                         "iomp5.a", "iomp5.so"]],
                                             'dirs': []
                                            })

            self.log.info("Customized sanity check paths: %s" % self.getcfg('sanityCheckPaths'))

        IntelBase.sanitycheck(self)
