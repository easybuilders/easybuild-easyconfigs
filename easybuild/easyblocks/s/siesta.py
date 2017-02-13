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
EasyBuild support for building and installing Siesta, implemented as an easyblock

@author: Ake Sandgren (Umea University)
"""
import os
import re
import shutil
import stat
import tempfile

import easybuild.tools.config as config
import easybuild.tools.environment as env
import easybuild.tools.toolchain as toolchain
from distutils.version import LooseVersion
from easybuild.easyblocks.generic.configuremake import ConfigureMake
from easybuild.framework.easyconfig import CUSTOM
from easybuild.tools.build_log import EasyBuildError
from easybuild.tools.filetools import adjust_permissions, mkdir, write_file
from easybuild.tools.modules import get_software_libdir, get_software_root, get_software_version
from easybuild.tools.run import run_cmd


class EB_Siesta(ConfigureMake):
    """
    Support for building/installing Siesta.
    - avoid parallel build, doesn't work
    """

    def __init__(self, *args, **kwargs):
        """Initialisation of custom class variables for Siesta."""
        super(EB_Siesta, self).__init__(*args, **kwargs)

    def configure_step(self):
        """
        Custom configure and build procedure for Siesta.
        - There are two main builds to do, siesta and transiesta
        - In addition there are multiple support tools to build
        """

        # Make a temp installdir during the build of the various parts
        bindir = os.path.join(self.cfg['start_dir'], 'bin')
        try:
            mkdir(bindir)
        except OSError, err:
            raise EasyBuildError("Failed to create temp installdir %s: %s", bindir, err)

        # change to actual build dir
        try:
            os.chdir('Obj')
        except OSError, err:
            raise EasyBuildError("Failed to change to build dir: %s", err)

        # Populate start_dir with makefiles
        run_cmd('../Src/obj_setup.sh', log_all=True, simple=True, log_output=True)

        # MPI?
        if self.toolchain.options.get('usempi', None):
            self.cfg.update('configopts', '--enable-mpi')

        # BLAS and LAPACK
        self.cfg.update('configopts', '--with-blas="$LIBBLAS"')
        self.cfg.update('configopts', '--with-lapack="$LIBLAPACK"')

        # ScaLAPACK (and BLACS)
        self.cfg.update('configopts', '--with-scalapack="$LIBSCALAPACK"')
        self.cfg.update('configopts', '--with-blacs="$LIBSCALAPACK"')

        # NetCDF-Fortran
        netcdff_loc = get_software_root('NetCDF-Fortran')
        if netcdff_loc:
            self.cfg.update('configopts', '--with-netcdf=-lnetcdff')

        super(EB_Siesta, self).configure_step(cmd_prefix='../Src/')

        run_cmd('make', log_all=True, simple=True, log_output=True)

        # Put binary in temporary install dir
        shutil.copy(os.path.join(self.cfg['start_dir'], 'Obj', 'siesta'),
                    bindir)

        # Make the utils
        try:
            os.chdir('../Util')
        except OSError, err:
            raise EasyBuildError("Failed to change to Util dir: %s", err)

        # clean_all.sh is missing executable bit...
        adjust_permissions('./clean_all.sh', stat.S_IXUSR, recursive=False, relative=True)
        run_cmd('./clean_all.sh', log_all=True, simple=True, log_output=True)
        run_cmd('./build_all.sh', log_all=True, simple=True, log_output=True)

        # Now move all the built utils to the temp installdir
        expected_utils = [
            'Eig2DOS/Eig2DOS',
            'TBTrans/tbtrans',
            'Vibra/Src/vibra', 'Vibra/Src/fcbuild',
            'SiestaSubroutine/SimpleTest/Src/simple_pipes_serial',
            'SiestaSubroutine/SimpleTest/Src/simple_pipes_parallel',
            'SiestaSubroutine/ProtoNEB/Src/protoNEB',
            'SiestaSubroutine/FmixMD/Src/para',
            'SiestaSubroutine/FmixMD/Src/driver',
            'SiestaSubroutine/FmixMD/Src/simple',
            'Denchar/Src/denchar',
            'pdosxml/pdosxml',
            'WFS/readwfx', 'WFS/wfsnc2wfsx', 'WFS/readwf', 'WFS/wfs2wfsx',
            'WFS/info_wfsx', 'WFS/wfsx2wfs',
            'HSX/hs2hsx', 'HSX/hsx2hs',
            'Optimizer/simplex', 'Optimizer/swarm',
            'ON/lwf2cdf',
            'DensityMatrix/dm2cdf', 'DensityMatrix/cdf2dm',
            'Helpers/get_chem_labels',
            'Grid/cdf2grid', 'Grid/cdf_laplacian', 'Grid/cdf2xsf',
            'Grid/grid_rotate', 'Grid/g2c_ng', 'Grid/grid2cdf', 'Grid/grid2val',
            'Grid/grid2cube',
            'Bands/new.gnubands', 'Bands/eigfat2plot',
            'Contrib/APostnikov/xv2xsf', 'Contrib/APostnikov/md2axsf',
            'Contrib/APostnikov/vib2xsf', 'Contrib/APostnikov/fmpdos',
            'Contrib/APostnikov/eig2bxsf', 'Contrib/APostnikov/rho2xsf',
            'JobList/Src/getResults', 'JobList/Src/countJobs',
            'JobList/Src/runJobs', 'JobList/Src/horizontal',
            'Projections/orbmol_proj',
            'COOP/mprop', 'COOP/dm_creator', 'COOP/fat',
            'TBTrans_rep/tbtrans',
            'Macroave/Src/macroave',
            'Gen-basis/ioncat', 'Gen-basis/gen-basis',
            'STM/simple-stm/plstm', 'STM/ol-stm/Src/stm',
            'VCA/mixps', 'VCA/fractional',
        ]
        for f in expected_utils:
            shutil.copy(os.path.join(self.cfg['start_dir'], 'Util', f),
                    bindir)

        # Build transiesta
        try:
            os.chdir('../Obj')
        except OSError, err:
            raise EasyBuildError("Failed to change back to Obj dir: %s", err)

        run_cmd('make clean', log_all=True, simple=True, log_output=True)
        run_cmd('make transiesta', log_all=True, simple=True, log_output=True)

        shutil.copy(os.path.join(self.cfg['start_dir'], 'Obj', 'transiesta'),
                    bindir)

    def build_step(self):
        """No build step for Siesta."""
        pass

    def install_step(self):
        """Custom install procedure for Siesta."""

        try:
            # binary
            bindir = os.path.join(self.installdir, 'bin')
            shutil.copytree(os.path.join(self.cfg['start_dir'], 'bin'),
                        bindir)

        except OSError, err:
            raise EasyBuildError("Failed to install Siesta: %s", err)

    def sanity_check_step(self):
        """Custom sanity check for Siesta."""

        custom_paths = {
            'files': ['bin/siesta', 'bin/transiesta', 'bin/denchar'],
            'dirs': [],
        }

        super(EB_Siesta, self).sanity_check_step(custom_paths=custom_paths)
