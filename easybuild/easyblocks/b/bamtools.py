##
# Copyright 2009-2016 The Cyprus Institute
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
EasyBuild support for BamTools, implemented as an easyblock

@author: Andreas Panteli (The Cyprus Institute)
@author: Kenneth Hoste (Ghent University)
"""
import os
from distutils.version import LooseVersion
from easybuild.easyblocks.generic.cmakemake import CMakeMake
from easybuild.easyblocks.generic.makecp import MakeCp
from easybuild.tools.build_log import EasyBuildError
from easybuild.tools.filetools import mkdir
from easybuild.tools.systemtools import get_shared_lib_ext


class EB_BamTools(MakeCp, CMakeMake):
    """Support for building and installing BamTools."""

    def configure_step(self):
        """Configure BamTools build."""
        # BamTools requires an out of source build.
        builddir = os.path.join(self.cfg['start_dir'], 'build')
        try:
            mkdir(builddir)
            os.chdir(builddir)
        except OSError, err:
            raise EasyBuildError("Failed to move to %s: %s", builddir, err)

        CMakeMake.configure_step(self, srcdir='..')

    def sanity_check_step(self):
        """Custom sanity check for BamTools."""

        sharedlib_ext = get_shared_lib_ext()

        custom_paths = {
            'files': [
                "bin/bamtools",
                "include/shared/bamtools_global.h",
                "lib/libbamtools.a",
                "lib/libbamtools.%s" % sharedlib_ext
            ],
            'dirs': [
                "include/api",
                "docs"
            ]
        }
        if LooseVersion(self.version) < LooseVersion('2.3.0'):
            # Buid environment changed:
            # https://github.com/pezmaster31/bamtools/commit/9cfa70bfe9cdf1b6adc06beb88246b45fdd6250a
            custom_paths['files'].extend([
                "lib/libbamtools-utils.%s" % sharedlib_ext,
                "lib/libjsoncpp.%s" % sharedlib_ext
            ])
        else:
            custom_paths['files'].extend([
                "lib/libbamtools-utils.a",
                "lib/libjsoncpp.a"
            ])
        super(EB_BamTools, self).sanity_check_step(custom_paths=custom_paths)
