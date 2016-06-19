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
EasyBlock for RepeatMasker

@author: Ruben van Dijk (University of Groningen)
"""
import os
import shutil

from easybuild.framework.easyblock import EasyBlock
from easybuild.easyblocks.generic.packedbinary import PackedBinary
from easybuild.tools.build_log import EasyBuildError
from easybuild.tools.run import run_cmd
from easybuild.tools.modules import get_software_root, get_software_version

class EB_RepeatMasker(PackedBinary):
    """
    Support for building RepeatMasker
    """

    def install_step(self):
        """Copy all unpacked source directories to install directory, one-by-one."""
        super(EB_RepeatMasker, self).install_step(self)
        
        
    def post_install_step(self):
        """Check an which search engine should be used for RepeatMasker"""
        
        # USE https://github.com/hpcugent/easybuild-easyblocks/blob/a5ca455fe34a2e3ff12d61849675f65b447f23e2/easybuild/easyblocks/x/xmipp.py
        dep_names = [dep['name'] for dep in self.cfg['dependencies']]
        for i in dep_names:
            print i

'''
kijk of 1 van 4 er instaat
hou rekening met meer dan 1, zet dan 1e op default.

run_cmd_qa gebruiken.
'''

"""Configure RepeatMasker"""
'''
perl_path = "\n" + self.toolchain.get_variable('')

 
mpi_support = 'Y'
mpi_inc_dir = self.toolchain.get_variable('MPI_INC_DIR')
mpicc = os.path.join(mpi_inc_dir, '..', 'bin', 'mpicc')
mpih = os.path.join(mpi_inc_dir, 'mpi.h')
input = '\n'.join([mpi_support, mpicc, mpih])
input = 'N'

'''
'''
input += '\n'
run_cmd('./configure', inp=input)
run_cmd('perl Build install')

'''
"""
# RepeatMasker has a configure that needs some input, if HMMER is preferred as search engine include HMMER as dependency and
# replace '2' with '4': 
postinstallcmds = [
"cd %(installdir)s && \
printf '\n\n\n\n%s\n%s\n\n%s\n' '2' $EBROOTRMBLAST '5' > conf.in && \
./configure < conf.in && rm conf.in",
'''
"""






