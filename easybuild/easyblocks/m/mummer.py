##
# Copyright 2009-2013 Ghent University
#
# This file is part of EasyBuild,
# originally created by the HPC team of the University of Ghent (http://ugent.be/hpc).
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
EasyBuild support for building and installing MUMmer, implemented as an easyblock

@author: Cedric Laczny (Uni.Lu)
@author: Fotis Georgatos (Uni.Lu)
@author: Kenneth Hoste (Ghent University)
@author: Jens Timmerman (Ghent University)
"""

import shutil

from easybuild.easyblocks.generic.configuremake import ConfigureMake
from easybuild.tools.filetools import run_cmd
from easybuild.tools.modules import get_software_root, get_software_version


class EB_MUMmer(ConfigureMake):
    """Support for building and installing MUMmer."""

    def configure_step(self):
        """Configure MUMmer build by running make check and setting make options."""

        # make sure Perl is available
        if not get_software_root('Perl'):
            self.log.error("Perl module not loaded?")

        cmd = "%s make check %s" % (self.cfg['preconfigopts'], self.cfg['configopts'])
        run_cmd(cmd, log_all=True, simple=True, log_output=True)

        self.cfg.update('makeopts', 'all')

    def install_step(self):
        """Install MUMmer by copying everything."""
        try:
            # remove actual installdir, shutil doesn't like it to be there
            shutil.rmtree(self.installdir)
            shutil.copytree(self.cfg['start_dir'], self.installdir, symlinks=True)
        except OSError, err:
            self.log.error("Failed to install MUMmer: %s" % err)

    def make_module_extra(self):
        """Correctly prepend $PATH and $PERLXLIB for MUMmer."""
        txt = super(EB_MUMmer, self).make_module_extra()
        txt += self.moduleGenerator.prepend_paths("PATH", [""])
        perlmajver = get_software_version('Perl').split('.')[0]
        txt += self.moduleGenerator.prepend_paths("PERL%sLIB" % perlmajver, ["scripts"])
        return txt

    def sanity_check_step(self):
        """Custom sanity check for MUMmer."""

        custom_paths =   {
            'files': ['mapview', 'combineMUMs', 'mgaps', 'run-mummer3', 'show-coords',
                      'show-snps', 'show-aligns', 'dnadiff', 'mummerplot',
                      'nucmer2xfig', 'annotate', 'promer', 'show-diff', 'nucmer',
                      'delta-filter', 'src', 'run-mummer1', 'gaps', 'mummer',
                      'repeat-match', 'show-tiling', 'exact-tandems'],
            'dirs': ['scripts', 'docs', 'aux_bin'],
        }

        super(EB_MUMmer, self).sanity_check_step(custom_paths=custom_paths)
