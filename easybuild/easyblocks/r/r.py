##
# Copyright 2012-2016 Ghent University
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
EasyBuild support for building and installing R, implemented as an easyblock

@author: Jens Timmerman (Ghent University)
"""
import os
from distutils.version import LooseVersion

from easybuild.easyblocks.generic.configuremake import ConfigureMake
from easybuild.tools import environment
from easybuild.tools.systemtools import get_shared_lib_ext


EXTS_FILTER_R_PACKAGES = ("R -q --no-save", "library(%(ext_name)s)")


class EB_R(ConfigureMake):
    """
    Build and install R, including list of libraries specified as extensions.
    Install specified version of libraries, install hard-coded library version
    or latest library version (in that order of preference)
    """

    def prepare_for_extensions(self):
        """
        We set some default configs here for R packages
        """
        # insert new packages by building them with RPackage
        self.cfg['exts_defaultclass'] = "RPackage"
        self.cfg['exts_filter'] = EXTS_FILTER_R_PACKAGES

    def configure_step(self):
        """Configuration step, we set FC, F77 is already set by EasyBuild to the right compiler,
        FC is used for Fortan90"""
        environment.setvar("FC", self.toolchain.get_variable('F90'))
        ConfigureMake.configure_step(self)
    
    def make_module_req_guess(self):
        """
        Add extra paths to modulefile
        """
        guesses = super(EB_R, self).make_module_req_guess()

        guesses.update({
            'LD_LIBRARY_PATH': ['lib64', 'lib', 'lib64/R/lib', 'lib/R/lib'],
            'LIBRARY_PATH': ['lib64', 'lib', 'lib64/R/lib', 'lib/R/lib'],
            'PKG_CONFIG_PATH': ['lib64/pkgconfig', 'lib/pkgconfig'],
        })

        return guesses

    def sanity_check_step(self):
        """Custom sanity check for R."""
        shlib_ext = get_shared_lib_ext()

        libfiles = [os.path.join('include', x) for x in ['Rconfig.h', 'Rdefines.h', 'Rembedded.h',
                                                         'R.h', 'Rinterface.h', 'Rinternals.h',
                                                         'Rmath.h', 'Rversion.h', 'S.h']]
        modfiles = ['internet.%s' % shlib_ext, 'lapack.%s' % shlib_ext]
        if LooseVersion(self.version) < LooseVersion('3.2'):
            modfiles.append('vfonts.%s' % shlib_ext)
        libfiles += [os.path.join('modules', x) for x in modfiles]
        libfiles += ['lib/libR.%s' % shlib_ext]

        custom_paths = {
            'files': ['bin/%s' % x for x in ['R', 'Rscript']] +
                     [(os.path.join('lib64', 'R', f), os.path.join('lib', 'R', f)) for f in libfiles],
            'dirs': [],
        }
        super(EB_R, self).sanity_check_step(custom_paths=custom_paths)
