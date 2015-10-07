##
# Copyright 2013 Ghent University
#
# This file is part of EasyBuild,
# originally created by the HPC team of Ghent University (http://ugent.be/hpc/en),
# with support of Ghent University (http://ugent.be/hpc),
# the Flemish Supercomputer Centre (VSC) (https://vscentrum.be/nl/en),
# the Hercules foundation (http://www.herculesstichting.be/in_English)
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
EasyBuild support for building and installing Bowtie, implemented as an easyblock

@author: Cedric Laczny (Uni.Lu)
@author: Fotis Georgatos (Uni.Lu)
@author: Kenneth Hoste (Ghent University)
@author: Jens Timmerman (Ghent University)
"""
from distutils.version import LooseVersion
import glob
import os
import shutil

from easybuild.easyblocks.generic.configuremake import ConfigureMake
from easybuild.tools.build_log import EasyBuildError


class EB_Bowtie(ConfigureMake):
    """
    Support for building bowtie (ifast and sensitive read alignment)
    """

    def configure_step(self):
        """
        Set compilers in buildopts, there is no configure script.
        """
        comp_opts = 'CC="%(cc)s" CXX="%(cxx)s" CPP="%(cxx)s"' % {'cc': os.getenv('CC'), 'cxx': os.getenv('CXX')}
        self.cfg.update('buildopts', comp_opts)

        # make sure install target is specified for recent Bowtie versions that support 'make install'
        if LooseVersion(self.version) >= LooseVersion('1.1.2'):
            self.cfg.update('installopts', "prefix=%s" % self.installdir)

    def install_step(self):
        """
        Install by copying files to install dir
        """
        if LooseVersion(self.version) >= LooseVersion('1.1.2'):
            # 'make install' is supported since Bowtie 1.1.2
            super(EB_Bowtie, self).install_step()
        else:
            srcdir = self.cfg['start_dir']
            destdir = os.path.join(self.installdir, 'bin')
            srcfile = None
            try:
                os.makedirs(destdir)
                for srcfile in glob.glob(os.path.join(srcdir, 'bowtie*')):
                    if not srcfile.endswith('.cpp'):
                        shutil.copy2(srcfile, destdir)
            except (IOError, OSError), err:
                raise EasyBuildError("Copying %s to installation dir %s failed: %s", srcfile, destdir, err)

    def sanity_check_step(self):
        """Custom sanity check for Bowtie."""
        binaries = ['bowtie', 'bowtie-build', 'bowtie-inspect']
        if LooseVersion(self.version) > LooseVersion('1.1.0'):
            binaries.extend(['bowtie-align-l', 'bowtie-align-s', 'bowtie-build-l', 'bowtie-build-s',
                             'bowtie-inspect-l', 'bowtie-inspect-s'])
        custom_paths = {
            'files': [os.path.join('bin', x) for x in binaries],
            'dirs': []
        }
        super(EB_Bowtie, self).sanity_check_step(custom_paths=custom_paths)
