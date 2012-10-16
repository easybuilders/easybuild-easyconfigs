##
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
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with EasyBuild. If not, see <http://www.gnu.org/licenses/>.
##
import os
from easybuild.framework.application import Application
from easybuild.tools.filetools import run_cmd, parselogForError

class EB_R(Application):
    """
    Install R, including list of packages specified
    Install specified version of packages, install hard-coded package version 
    or latest package version (in that order of preference) 
    """
    def extra_packages_pre(self):
        """
        We set some default configs here for extentions for R.
        """
        self.setcfg('pkgtemplate', "%s_%s.tar.gz")
        self.setcfg('pkgdefaultclass', ['easybuild.easyblocks.rpackage', "EB_RPackage"])
        self.setcfg('pkgfilter', ["R -q --no-save", "library(%(name)s)"])
        self.setcfg('pkgtemplate', '%(name)s/%(name)s_%(version)s.tar.gz')
        self.setcfg('pkginstalldeps', True)
