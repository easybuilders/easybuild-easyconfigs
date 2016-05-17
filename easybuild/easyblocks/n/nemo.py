##
# Copyright 2015-2016 Ghent University
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
EasyBuild support for building and installing NEMO, implemented as an easyblock

@author: Oriol Mula-Valls (IC3)
"""
import os
import shutil

from easybuild.framework.easyblock import EasyBlock
from easybuild.framework.easyconfig import CUSTOM, MANDATORY
from easybuild.tools.build_log import EasyBuildError
from easybuild.tools.filetools import write_file
from easybuild.tools.modules import get_software_root
from easybuild.tools.run import run_cmd


class EB_NEMO(EasyBlock):
    """Support for building/installing NEMO."""

    def __init__(self, *args, **kwargs):
        """Initialisation of custom class variables for NEMO."""
        super(EB_NEMO, self).__init__(*args, **kwargs)

        self.conf_name = 'EB_NEMO_CONFIG'
        self.conf_arch_file = 'NEMOGCM/ARCH/arch-eb.fcm'

    @staticmethod
    def extra_options():
        """Custom easyconfig parameters for NEMO."""
        extra_vars = {
            'with_components': [None, "List of components to include (e.g. TOP_SRC)", MANDATORY],
            'add_keys': [None, "Add compilation keys", CUSTOM],
            'del_keys': [None, "Delete compilation keys", CUSTOM]
        }
        return EasyBlock.extra_options(extra_vars)

    def configure_step(self):
        """Custom configuration procedure for NEMO."""
        netcdf_fortran_root = get_software_root('netCDF-Fortran')
        if not netcdf_fortran_root:
            raise EasyBuildError("netCDF-Fortran is not available, but is a required dependency")

        cfg = '\n'.join([
            "%%NCDF_INC -I%s/include" % netcdf_fortran_root,
            "%%NCDF_LIB -L%s/lib -lnetcdff" % netcdf_fortran_root,
            "%%FC %s" % os.getenv('F90'),
            "%FCFLAGS -r8 -O3  -traceback",
            "%FFLAGS %FCFLAGS",
            "%LD %FC",
            "%LDFLAGS ",
            "%FPPFLAGS -P -C",
            "%AR ar",
            "%ARFLAGS rs",
            "%MK make",
            "%USER_INC %NCDF_INC",
            "%USER_LIB %NCDF_LIB"
        ])
        write_file(self.conf_arch_file, cfg)

        cmd = "./makenemo -n %s -d '%s' -j0 -m eb" % (self.conf_name, ' '.join(self.cfg['with_components']))

        if self.cfg['add_keys'] is not None:
            cmd += " add_key '%s'" % ' '.join(self.cfg['add_keys'])
        if self.cfg['del_keys'] is not None:
            cmd += " del_key '%s'" % ' '.join(self.cfg['del_keys'])

        try:
            dst = 'NEMOGCM/CONFIG'
            os.chdir(dst)
            self.log.debug("Changed to directory %s", dst)
        except OSError, err:
            raise EasyBuildError("Failed to change to directory %s: %s", dst, err)

        run_cmd(cmd, log_all=True, simple=True, log_ok=True)

    def build_step(self):
        """Custom build procedure for NEMO."""
        cmd = "./makenemo -n %s -m eb" % self.conf_name
        run_cmd(cmd, log_all=True, simple=True, log_ok=True)

    def install_step(self):
        """Custom install procedure for NEMO."""
        binpath = os.path.join(self.cfg['start_dir'], 'NEMOGCM', 'CONFIG', self.conf_name, 'BLD/bin')
        try:
            shutil.copytree(binpath, os.path.join(self.installdir, 'bin'))
        except OSError, err:
            raise EasyBuildError("Copying %s to installation dir failed: %s", binpath, err)

    def sanity_check_step(self):
        """Custom sanity check for NEMO."""
        custom_paths = {
            'files': ['bin/nemo.exe'],
            'dirs': [],
        }
        super(EB_NEMO, self).sanity_check_step(custom_paths=custom_paths)
