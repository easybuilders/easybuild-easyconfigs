##
# Copyright 2014 Ghent University
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
EasyBuild support for building and installing Xmlm, implemented as an easyblock

@author: Kenneth Hoste (Ghent University)
"""
from easybuild.easyblocks.generic.makecp import MakeCp
from easybuild.framework.easyconfig import CUSTOM
from easybuild.tools.filetools import run_cmd


class EB_Xmlm(MakeCp):
    """Support for building/installing Xmlm."""

    @staticmethod
    def extra_options():
        """
        Define list of files or directories to be copied after make
        """
        extra_vars = dict(MakeCp.extra_options())
        extra_vars['files_to_copy'] = [[
            (['_build/src/xmlm.*', '_build/pkg/META'], 'site-lib/xmlm'),
            (['_build/test/xmltrip.native'], 'bin/xmltrip'),
            (['_build/*.md', '_build/test/*.ml'], ''),
        ], "List of files to copy", CUSTOM]
        return MakeCp.extra_options(extra_vars=extra_vars)

    def build_step(self):
        """Custom build procedure for Xmlm."""
        cmd = "./pkg/build true"
        run_cmd(cmd, log_all=True, simple=True, log_ok=True)

    def make_module_extra(self):
        """Custom extra module file entries for Xmlm."""
        txt = super(EB_Xmlm, self).make_module_extra()
        txt += self.moduleGenerator.prepend_paths("OCAMLPATH", ['site-lib'])
        return txt

    def sanity_check_step(self):
        """Custom sanity check for Xmlm."""
        custom_paths = {
            'files': ['bin/xmltrip', 'site-lib/xmlm/META', 'site-lib/xmlm/xmlm.a', 'site-lib/xmlm/xmlm.mli'] +
                     ['site-lib/xmlm/xmlm.cm%s' % x for x in ['a', 'i', 'o', 't', 'x', 'xa', 'xs']],
            'dirs': [],
        }
        super(EB_Xmlm, self).sanity_check_step(custom_paths=custom_paths)
