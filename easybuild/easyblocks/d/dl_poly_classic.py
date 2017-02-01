##
# Copyright 2013-2017 Ghent University
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
from easybuild.tools.filetools import copy_file, copytree
from easybuild.tools.run import run_cmd
from easybuild.easyblocks.generic.configuremake import ConfigureMake


class EB_DL_underscore_POLY_underscore_Classic(ConfigureMake):
    """Support for building and installing DL_POLY Classic."""

    def __init__(self, *args, **kwargs):
        """Easyblock constructor; initialize class variables."""
        super(EB_DL_underscore_POLY_underscore_Classic, self).__init__(*args, **kwargs)

        # check whether PLUMED is listed as a dependency
        self.with_plumed = 'PLUMED' in [dep['name'] for dep in self.cfg['dependencies']]

    # create PLUMED patch in prepare_step rather than patch_step,
    # so we can rely on being in the unpacked source directory
    def prepare_step(self):
        """Generate PLUMED patch if PLUMED is listed as a dependency."""
        super(EB_DL_underscore_POLY_underscore_Classic, self).prepare_step()

        if self.with_plumed:
            # see https://groups.google.com/d/msg/plumed-users/cWaIDU5F6Bw/bZUW3J9cCAAJ
            diff_pat = 'dlpoly-*.diff'
            try:
                diff_hits = glob.glob(os.path.join(self.builddir, diff_pat))
            except OSError as err:
                raise EasyBuildError("Failed to find list of files/dirs that match '%s': %s", diff_pat, err)

            if len(diff_hits) == 1:
                plumed_patch = diff_hits[0]
            elif not self.dry_run:
                raise EasyBuildError("Expected to find exactly one match for '%s' in %s, found: %s",
                                     diff_pat, self.builddir, diff_hits)

            if not self.dry_run:
                try:
                    os.rename('source', 'srcmod')
                except OSError as err:
                    raise EasyBuildError("Failed to move 'source' directory to 'srcmod': %s", err)

            engine = os.path.splitext(os.path.basename(plumed_patch))[0]
            cmd = "plumed-patch -p --runtime -e %s -d %s" % (engine, plumed_patch)
            run_cmd(cmd, log_all=True, simple=True)

    def configure_step(self):
        """Copy the makefile to the source directory and use MPIF90 to do a parrallel build"""

        self.cfg.update('buildopts', 'LD="$MPIF90 -o" FC="$MPIF90 -c" par')

        if self.with_plumed:
            source_dir = 'srcmod'
            self.cfg.update('buildopts', 'LDFLAGS="${LDFLAGS} -lplumed -ldl"')
        else:
            source_dir = 'source'

        copy_file(os.path.join('build', 'MakePAR'), os.path.join(source_dir, 'Makefile'))
        try:
            os.chdir(source_dir)
        except OSError as err:
            raise EasyBuildError("Failed to change to %s: %s", source_dir, err)

    def install_step(self):
        """Copy the executables to the installation directory"""
        self.log.debug("copying %s/execute to %s, (from %s)", self.cfg['start_dir'], self.installdir, os.getcwd())
        # create a 'bin' subdir, this way we also get $PATH to be set correctly automatically
        install_path = os.path.join(self.cfg['start_dir'], 'execute')
        bin_path = os.path.join(self.installdir, 'bin')
        copytree(install_path, bin_path)

    def sanity_check_step(self):
        """Custom sanity check step for DL_POLY Classic"""
        custom_paths = {
            'files': ['bin/DLPOLY.X'],
            'dirs': [],
        }
        super(EB_DL_underscore_POLY_underscore_Classic, self).sanity_check_step(custom_paths=custom_paths)
