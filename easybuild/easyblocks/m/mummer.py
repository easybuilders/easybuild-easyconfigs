##
# Copyright 2009-2016 Ghent University
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
#
# This work implements a part of the HPCBIOS project and is a component of the policy:
# http://hpcbios.readthedocs.org/en/latest/HPCBIOS_2012-94.html
##
"""
EasyBuild support for building and installing MUMmer, implemented as an easyblock

@author: Cedric Laczny (Uni.Lu)
@author: Fotis Georgatos (Uni.Lu)
@author: Kenneth Hoste (Ghent University)
@author: Jens Timmerman (Ghent University)
@author: Matt Lesko (NIH/NHGRI)
"""

import fileinput
import re
import os
import shutil
import sys

from easybuild.easyblocks.generic.configuremake import ConfigureMake
from easybuild.easyblocks.perl import get_major_perl_version
from easybuild.tools.build_log import EasyBuildError
from easybuild.tools.run import run_cmd


class EB_MUMmer(ConfigureMake):
    """Support for building and installing MUMmer (rapidly aligning entire genomes)."""

    def __init__(self, *args, **kwargs):
        """Define list of bin/aux_bin files."""

        super(EB_MUMmer, self).__init__(*args, **kwargs)

        self.bin_files = [
            "mummer", "annotate", "combineMUMs", "delta-filter", "gaps", "mgaps",
            "repeat-match", "show-aligns", "show-coords", "show-tiling", "show-snps",
            "show-diff", "exact-tandems", "mapview", "mummerplot", "nucmer", "promer",
            "run-mummer1", "run-mummer3", "nucmer2xfig", "dnadiff",
        ]
        self.script_files = ["Foundation.pm"]
        self.aux_bin_files = ["postnuc", "postpro", "prenuc", "prepro"]

    def configure_step(self):
        """Configure MUMmer build by running make check and setting make options."""

        cmd = "%s make check %s" % (self.cfg['preconfigopts'], self.cfg['configopts'])
        run_cmd(cmd, log_all=True, simple=True, log_output=True)

        self.cfg.update('buildopts', 'all')

    def install_step(self):
        """Patch files to avoid use of build dir, install by copying files to install dir."""
        # patch build dir out of files, replace by install dir
        for fil in [f for f in os.listdir(self.cfg['start_dir']) if os.path.isfile(f)]:
            self.log.debug("Patching build dir out of %s, replacing by install bin dir)" % fil)
            pat = r'%s' % self.cfg['start_dir']
            if pat[-1] == os.path.sep:
                pat = pat[:-1]
            for line in fileinput.input(fil, inplace=1, backup='.orig.eb'):
                line = re.sub(pat, os.path.join(self.installdir, 'bin'), line)
                sys.stdout.write(line)
        # copy files to install dir
        file_tuples = [
            (self.cfg['start_dir'], 'bin', self.bin_files),
            (os.path.join(self.cfg['start_dir'], 'aux_bin'), os.path.join('bin', 'aux_bin'), self.aux_bin_files),
            (os.path.join(self.cfg['start_dir'], 'scripts'), os.path.join('bin', 'scripts'), self.script_files),
        ]
        for srcdir, dest, files in file_tuples:
            destdir = os.path.join(self.installdir, dest)
            srcfile = None
            try:
                os.makedirs(destdir)
                for filename in files:
                    srcfile = os.path.join(srcdir, filename)
                    shutil.copy2(srcfile, destdir)

            except OSError, err:
                raise EasyBuildError("Copying %s to installation dir %s failed: %s", srcfile, destdir, err)

    def make_module_extra(self):
        """Correctly prepend $PATH and $PERLXLIB for MUMmer."""
        # determine major version for Perl (e.g. '5'), required for e.g. $PERL5LIB
        perlmajver = get_major_perl_version()

        # set $PATH and $PERLXLIB correctly
        txt = super(EB_MUMmer, self).make_module_extra()
        txt += self.module_generator.prepend_paths("PATH", ['bin'])
        txt += self.module_generator.prepend_paths("PATH", ['bin/aux_bin'])
        txt += self.module_generator.prepend_paths("PERL%sLIB" % perlmajver, ['bin/scripts'])
        return txt

    def sanity_check_step(self):
        """Custom sanity check for MUMmer."""

        custom_paths = {
            'files':
                ['bin/%s' % x for x in self.bin_files] +
                ['bin/aux_bin/%s' % x for x in self.aux_bin_files] +
                ['bin/scripts/%s' % x for x in self.script_files],
            'dirs': []
        }
        super(EB_MUMmer, self).sanity_check_step(custom_paths=custom_paths)
