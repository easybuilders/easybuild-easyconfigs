##
# Copyright 2009-2017 Ghent University
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
EasyBuild support for MyMediaLite, implemented as an easyblock

@author: Stijn De Weirdt (Ghent University)
@author: Dries Verdegem (Ghent University)
@author: Kenneth Hoste (Ghent University)
@author: Pieter De Baets (Ghent University)
@author: Jens Timmerman (Ghent University)
"""

from distutils.version import LooseVersion

from easybuild.easyblocks.generic.configuremake import ConfigureMake
from easybuild.tools.run import run_cmd


class EB_MyMediaLite(ConfigureMake):
    """Support for building/installing MyMediaLite."""

    def configure_step(self):
        """Custom configure step for MyMediaLite, using "make CONFIGURE_OPTIONS='...' configure"."""

        if LooseVersion(self.version) < LooseVersion('3'):
            cmd = "make CONFIGURE_OPTIONS='--prefix=%s' configure" % self.installdir
            run_cmd(cmd, log_all=True, simple=True)
        else:
            self.cfg.update('installopts', "PREFIX=%s" % self.installdir)

    def build_step(self):
        """Custom build step for MyMediaLite, using 'make all' in 'src' directory."""

        cmd = "cd src && make all && cd .."
        run_cmd(cmd, log_all=True, simple=True)

    def sanity_check_step(self):
        """Custom sanity check for MyMediaLite."""

        if LooseVersion(self.version) < LooseVersion('3'):
            bin_files = ["bin/%s_prediction" % x for x in ['item', 'mapping_item', 'mapping_rating', 'rating']]
        else:
            bin_files = ["bin/item_recommendation", "bin/rating_based_ranking", "bin/rating_prediction"]

        custom_paths = {
            'files': bin_files,
            'dirs': ["lib/mymedialite"],
        }
        super(EB_MyMediaLite, self).sanity_check_step(custom_paths=custom_paths)
