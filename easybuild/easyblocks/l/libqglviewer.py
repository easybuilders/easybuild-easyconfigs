##
# Copyright 2009-2016 Ghent University
#
# This file is part of EasyBuild,
# originally created by the HPC team of Ghent University (http://ugent.be/hpc/en),
# with support of Ghent University (http://ugent.be/hpc),
# the Flemish Supercomputer Centre (VSC) (https://vscentrum.be/nl/en),
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


class EB_libQGLViewer(ConfigureMake):
    """Support for building/installing libQGLViewer."""

    def __init__(self, *args, **kwargs):
        """Initialisation of custom class variables for libQGLViewer."""
        super(EB_libQGLViewer, self).__init__(*args, **kwargs)        

    def configure_step(self, cmd_prefix=''):
        """Custom configuration procedure for libQGLViewer.        
        - typically ./qmake --prefix=/install/path style
        """

        if self.cfg.get('configure_cmd_prefix'):
            if cmd_prefix:
                tup = (cmd_prefix, self.cfg['configure_cmd_prefix'])
                self.log.debug("Specified cmd_prefix '%s' is overruled by configure_cmd_prefix '%s'" % tup)
            cmd_prefix = self.cfg['configure_cmd_prefix']

        if self.cfg.get('tar_config_opts'):
            # setting am_cv_prog_tar_ustar avoids that configure tries to figure out (in this case qmake)
            # which command should be used for tarring/untarring
            # am__tar and am__untar should be set to something decent (tar should work)
            tar_vars = {
                'am__tar': 'tar chf - "$$tardir"',
                'am__untar': 'tar xf -',
                'am_cv_prog_tar_ustar': 'easybuild_avoid_ustar_testing'
            }
            for (key, val) in tar_vars.items():
                self.cfg.update('preconfigopts', "%s='%s'" % (key, val))

        cmd = "%(preconfigopts)s %(cmd_prefix)sqmake PREFIX=%(installdir)s %(configopts)s" % {
            'preconfigopts': self.cfg['preconfigopts'],
            'cmd_prefix': cmd_prefix,
            'installdir': self.installdir,
            'configopts': self.cfg['configopts'],
        }

        (out, _) = run_cmd(cmd, log_all=True, simple=False)

        return out

    def build_step(self, verbose=False, path=None):
        """
        Start the actual build
        - typical: make
        """

        paracmd = ''
        if self.cfg['parallel']:
            paracmd = "-j %s" % self.cfg['parallel']

        cmd = "%s make %s %s" % (self.cfg['prebuildopts'], paracmd, self.cfg['buildopts'])
        
        (out, _) = run_cmd(cmd, path=path, log_all=True, simple=False, log_output=verbose)

        return out

    def sanity_check_step(self):
        """Custom sanity check for libQGLViewer."""

        custom_paths = {
                        'files': ['lib/libQGLViewer.prl', 'lib/libQGLViewer.so', 'lib/libQGLViewer.so.2', 'lib/libQGLViewer.so.2.5', 'lib/libQGLViewer.so.2.5.1'],
                        'dirs': ['include/QGLViewer'],
                       }

        super(EB_libQGLViewer, self).sanity_check_step(custom_paths=custom_paths)
