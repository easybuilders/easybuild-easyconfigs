##
# Copyright 2013-2016 Ghent University
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
EasyBuild support for DL_POLY Classic, implemented as an easyblock

@author: Jens Timmerman (Ghent University)
@author: Kenneth Hoste (Ghent University)
"""
import glob
import os
import shutil

from easybuild.tools.build_log import EasyBuildError
from easybuild.tools.filetools import copytree
from easybuild.tools.run import run_cmd
from easybuild.easyblocks.generic.makecp import MakeCp


class EB_DL_underscore_POLY_underscore_Classic(MakeCp):
    """Support for building and installing DL_POLY Classic."""

    def __init__(self, *args, **kwargs):
        """Easyblock constructor; initialize class variables."""
        super(EB_DL_underscore_POLY_underscore_Classic, self).__init__(*args, **kwargs)

        # check whether PLUMED is listed as a dependency
        self.with_plumed = 'PLUMED' in [dep['name'] for dep in self.cfg['dependencies']]

    def extract_step(self):
        """Move 'source' to 'srcmod' directory if PLUMED is used as a dependency."""
        super(EB_DL_underscore_POLY_underscore_Classic, self).extract_step()

        if self.with_plumed and not self.dry_run:
            try:
                os.rename('source', 'srcmod')
            except OSError as err:
                raise EasyBuildError("Failed to move 'source' directory to 'srcmod': %s", err)

    def patch_step(self):
        """Generate PLUMED patch if PLUMED is listed as a dependency."""
        diff_pat = 'dlpoly-*.diff'
        try:
            diff_hits = glob.glob(os.path.join(self.builddir, diff_pat))
        except OSError as err:
            raise EasyBuildError("Failed to find list of files/dirs that match '%s': %s", diff_pat, err)

        if len(diff_hits) == 1:
            plumed_patch = os.path.splitext(os.path.basename(diff_hits[0]))[0]
        else:
            raise EasyBuildError("Expected to find exactly one match for '%s', found: %s", diff_pat, diff_hits)

        run_cmd("plumed-patch -p --runtime %s -d %s.diff" % (plumed_patch, os.path.join(self.builddir, plumed_patch)))

        super(EB_DL_underscore_POLY_underscore_Classic, self).patch_step()

    def configure_step(self):
        """Copy the makefile to the source directory and use MPIF90 to do a parrallel build"""

        self.cfg.update('buildopts', 'LD="$MPIF90 -o" FC="$MPIF90 -c" par')

        if self.with_plumed:
            source_dir = 'srcmod'
        else:
            source_dir = 'source'

        try:
            shutil.copy(os.path.join('build', 'MakePAR'), os.path.join(source_dir, 'Makefile'))
            os.chdir(source_dir)

        except OSError as err:
            raise EasyBuildError("Failed to prepare configuration in %s: %s", source_dir, err)

        self.cfg['with_configure'] = True

        super(EB_DL_underscore_POLY_underscore_Classic, self).configure_step()

    def install_step(self):
        """Copy the executables to the installation directory"""
        self.log.debug("copying %s/execute to %s, (from %s)", self.cfg['start_dir'], self.installdir, os.getcwd())
        # create a 'bin' subdir, this way we also get $PATH to be set correctly automatically
        install_path = os.path.join(self.cfg['start_dir'], 'execute')
        bin_path = os.path.join(self.installdir, 'bin')
        copytree(install_path, bin_path)
