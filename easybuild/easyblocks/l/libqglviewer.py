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
EasyBuild support for building and installing libQGLViewer, implemented as an easyblock

@author: Javier Antonio Ruiz Bosch (Central University "Marta Abreu" of Las Villas, Cuba)
"""

from easybuild.easyblocks.generic.configuremake import ConfigureMake
from easybuild.tools.run import run_cmd
from easybuild.tools.systemtools import get_shared_lib_ext

class EB_libQGLViewer(ConfigureMake):
    """Support for building/installing libQGLViewer."""

    def configure_step(self):
        """Custom configuration procedure for libQGLViewer: qmake PREFIX=/install/path ..."""

        cmd = "%(preconfigopts)s qmake PREFIX=%(installdir)s %(configopts)s" % {
            'preconfigopts': self.cfg['preconfigopts'],            
            'installdir': self.installdir,
            'configopts': self.cfg['configopts'],
        }
        run_cmd(cmd, log_all=True, simple=True)

    def sanity_check_step(self):
        """Custom sanity check for libQGLViewer."""
        shlib_ext = get_shared_lib_ext()
        
        custom_paths = {
            'files': [('lib/libQGLViewer.prl', 'lib64/libQGLViewer.prl'),
		      ('lib/libQGLViewer.%s' % shlib_ext, 'lib64/libQGLViewer.%s' % shlib_ext)],
            'dirs': ['include/QGLViewer'],
        }
