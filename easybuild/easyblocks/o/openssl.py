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
EasyBuild support for OpenSSL, implemented as an easyblock

@author: Kenneth Hoste (Ghent University)
@author: Jens Timmerman (Ghent University)
"""
import os

from easybuild.easyblocks.generic.configuremake import ConfigureMake
from easybuild.tools.build_log import EasyBuildError
from easybuild.tools.run import run_cmd


class EB_OpenSSL(ConfigureMake):
    """Support for building OpenSSL"""

    def configure_step(self, cmd_prefix=''):
        """
        Configure step
        """
 
        cmd = "%s %s./config --prefix=%s threads shared %s" % (self.cfg['preconfigopts'], cmd_prefix,
                                                               self.installdir, self.cfg['configopts'])

        (out, _) = run_cmd(cmd, log_all=True, simple=False)

        return out

    def sanity_check_step(self):
        """Custom sanity check"""

        libdir = None
        for libdir_cand in ['lib', 'lib64']:
            if os.path.exists(os.path.join(self.installdir, libdir_cand)):
                libdir = libdir_cand
        if libdir is None:
            raise EasyBuildError("Failed to determine library directory.")

        custom_paths = {
            'files': [os.path.join(libdir, x) for x in ['libcrypto.a', 'libcrypto.so', 'libcrypto.so.1.0.0',
                                                        'libssl.a', 'libssl.so', 'libssl.so.1.0.0']] +
                     ['bin/openssl'],
            'dirs': [os.path.join(libdir, 'engines')],
        }

        super(EB_OpenSSL, self).sanity_check_step(custom_paths=custom_paths)
    
