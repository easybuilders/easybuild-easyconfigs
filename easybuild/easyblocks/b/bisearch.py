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
EasyBuild support for BiSearch, implemented as an easyblock

@author: Stijn De Weirdt (Ghent University)
@author: Dries Verdegem (Ghent University)
@author: Kenneth Hoste (Ghent University)
@author: Pieter De Baets (Ghent University)
@author: Jens Timmerman (Ghent University)
"""
import os

from easybuild.framework.easyblock import EasyBlock
from easybuild.tools.run import run_cmd_qa


class EB_BiSearch(EasyBlock):
    """
    Support for building BiSearch.
    Basically just run the interactive installation script install.sh.
    """

    def configure_step(self):
        """(no configure)"""
        pass

    def build_step(self):
        """(empty, building is performed in make_install step)"""
        pass

    def install_step(self):
        cmd = "./install.sh"

        qanda = {
                 'Please enter the BiSearch root directory: ': self.installdir,
                 'Please enter the path of c++ compiler [/usr/bin/g++]: ': os.getenv('CXX')
                }

        no_qa = [r'Compiling components\s*\.*']

        run_cmd_qa(cmd, qanda, no_qa=no_qa, log_all=True, simple=True)

    def sanity_check_step(self):
        """Custom sanity check for BiSearch."""

        custom_paths = {
                        'files':["bin/%s" % x for x in ["fpcr", "indexing_cdna",
                                                        "indexing_genome", "makecomp"]],
                        'dirs':[]
                       }

        super(EB_BiSearch, self).sanity_check_step(custom_paths=custom_paths)
