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
EasyBuild support for BiSearch, implemented as an easyblock
"""
import os

from easybuild.framework.application import Application
from easybuild.tools.filetools import run_cmd_qa


class EB_BiSearch(Application):
    """
    Support for building BiSearch.
    Basically just run the interactive installation script install.sh.
    """

    def configure(self):
        """(no configure)"""
        pass

    def make(self):
        """(empty, building is performed in make_install step)"""
        pass

    def make_install(self):
        cmd = "./install.sh"

        qanda = {
                 'Please enter the BiSearch root directory: ': self.installdir,
                 'Please enter the path of c++ compiler [/usr/bin/g++]: ': os.getenv('CXX')
                }

        no_qa = [r'Compiling components\s*\.*']

        run_cmd_qa(cmd, qanda, no_qa=no_qa, log_all=True, simple=True)

    def sanitycheck(self):
        """Custom sanity check for BiSearch."""

        if not self.getcfg('sanityCheckPaths'):
            self.setcfg('sanityCheckPaths', {'files':["bin/%s" % x for x in ["fpcr", "indexing_cdna",
                                                                             "indexing_genome", "makecomp"]],
                                             'dirs':[]
                                            }
                        )

            self.log.info("Customized sanity check paths: %s" % self.getcfg('sanityCheckPaths'))

        Application.sanitycheck(self)
