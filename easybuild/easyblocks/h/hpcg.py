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
EasyBuild support for building and installing HPCG, implemented as an easyblock

@author: Kenneth Hoste (Ghent University)
"""
import glob
import os
import re
import shutil

from easybuild.easyblocks.generic.configuremake import ConfigureMake
from easybuild.tools.build_log import EasyBuildError
from easybuild.tools.filetools import mkdir
from easybuild.tools.run import run_cmd


class EB_HPCG(ConfigureMake):
    """Support for building/installing HPCG."""

    def configure_step(self):
        """Custom configuration procedure for HPCG."""

        mkdir("obj")
        # configure with most generic configuration available, i.e. hybrid
        # this is not specific to GCC or OpenMP, we take full control over that via $CXX and $CXXFLAGS
        cmd = "../configure ../setup/Make.MPI_GCC_OMP" 
        run_cmd(cmd, log_all=True, simple=True, log_ok=True, path='obj')

    def build_step(self):
        """Run build in build subdirectory."""
        cxx = os.environ['CXX']
        cxxflags = os.environ['CXXFLAGS']
        cmd = "make CXX='%s' CXXFLAGS='$(HPCG_DEFS) %s -DMPICH_IGNORE_CXX_SEEK'" % (cxx, cxxflags)
        run_cmd(cmd, log_all=True, simple=True, log_ok=True, path='obj')

    def test_step(self):
        """Custom built-in test procedure for HPCG."""
        objbindir = os.path.join(self.cfg['start_dir'], 'obj', 'bin')
        # obtain equivalent of 'mpirun -np 2 xhpcg'
        hpcg_mpi_cmd = self.toolchain.mpi_cmd_for("xhpcg", 2)
        # 2 threads per MPI process (4 threads in total)
        cmd = "PATH=%s:$PATH OMP_NUM_THREADS=2 %s" % (objbindir, hpcg_mpi_cmd)
        run_cmd(cmd, simple=True, log_all=True, log_ok=True)

        # find log file, check for success
        success_regex = re.compile(r"Scaled Residual \[[0-9.e-]+\]")
        try:
            hpcg_logs = glob.glob('hpcg_log*txt')
            if len(hpcg_logs) == 1:
                txt = open(hpcg_logs[0], 'r').read()
                self.log.debug("Contents of HPCG log file %s: %s" % (hpcg_logs[0], txt))
                if success_regex.search(txt):
                    self.log.info("Found pattern '%s' in HPCG log file %s, OK!", success_regex.pattern, hpcg_logs[0])
                else:
                    raise EasyBuildError("Failed to find pattern '%s' in HPCG log file %s",
                                         success_regex.pattern, hpcg_logs[0])
            else:
                raise EasyBuildError("Failed to find exactly one HPCG log file: %s", hpcg_logs)
        except OSError, err:
            raise EasyBuildError("Failed to check for success in HPCG log file: %s", err)

    def install_step(self):
        """Custom install procedure for HPCG."""
        objbindir = os.path.join(self.cfg['start_dir'], 'obj', 'bin')
        bindir = os.path.join(self.installdir, 'bin')
        try:
            shutil.copytree(objbindir, bindir)
        except OSError, err:
            raise EasyBuildError("Failed to copy HPCG files to %s: %s", bindir, err)

    def sanity_check_step(self):
        """Custom sanity check for HPCG."""
        custom_paths = {
            'files': ['bin/xhpcg', 'bin/hpcg.dat'],
            'dirs': [],
        }
        super(EB_HPCG, self).sanity_check_step(custom_paths=custom_paths)
