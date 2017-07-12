##
# Copyright 2009-2017 Ghent University
#
# This file is part of EasyBuild,
# originally created by the HPC team of Ghent University (http://ugent.be/hpc/en),
# with support of Ghent University (http://ugent.be/hpc),
# the Flemish Supercomputer Centre (VSC) (https://www.vscentrum.be),
# Flemish Research Foundation (FWO) (http://www.fwo.be/en)
# and the Department of Economy, Science and Innovation (EWI) (http://www.ewi-vlaanderen.be/en).
#
# https://github.com/easybuilders/easybuild
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
EasyBuild support for ABAQUS, implemented as an easyblock

@author: Stijn De Weirdt (Ghent University)
@author: Dries Verdegem (Ghent University)
@author: Kenneth Hoste (Ghent University)
@author: Pieter De Baets (Ghent University)
@author: Jens Timmerman (Ghent University)
"""
from distutils.version import LooseVersion
import glob
import os

from easybuild.easyblocks.generic.binary import Binary
from easybuild.framework.easyblock import EasyBlock
from easybuild.tools.build_log import EasyBuildError
from easybuild.tools.environment import setvar
from easybuild.tools.filetools import change_dir, write_file
from easybuild.tools.run import run_cmd_qa


class EB_ABAQUS(Binary):
    """Support for installing ABAQUS."""

    def __init__(self, *args, **kwargs):
        """Initialisation of custom class variables for ABAQUS."""
        super(EB_ABAQUS, self).__init__(*args, **kwargs)
        self.replayfile = None

    def extract_step(self):
        """Use default extraction procedure instead of the one for the Binary easyblock."""
        EasyBlock.extract_step(self)

    def configure_step(self):
        """Configure ABAQUS installation."""
        if LooseVersion(self.version) >= LooseVersion('2016'):
            # skip checking of Linux version
            setvar('DSY_Force_OS', 'linux_a64')
            # skip checking of license server
            setvar('NOLICENSECHECK', 'true')
        else:
            self.replayfile = os.path.join(self.builddir, "installer.properties")
            txt = '\n'.join([
                "INSTALLER_UI=SILENT",
                "USER_INSTALL_DIR=%s" % self.installdir,
                "MAKE_DEF_VER=true",
                "DOC_ROOT=UNDEFINED",
                "DOC_ROOT_TYPE=false",
                "DOC_ROOT_ESCAPED=UNDEFINED",
                "ABAQUSLM_LICENSE_FILE=@abaqusfea",
                "LICENSE_SERVER_TYPE=FLEXNET",
                "PRODUCT_NAME=Abaqus %s" % self.version,
                "TMPDIR=%s" % self.builddir,
                "INSTALL_MPI=1",
            ])
            write_file(self.replayfile, txt)

    def install_step(self):
        """Install ABAQUS using 'setup'."""
        if LooseVersion(self.version) >= LooseVersion('2016'):
            change_dir(os.path.join(self.cfg['start_dir'], '1'))
            qa = {
                "Enter selection (default: Install):": '',
            }
            no_qa = [
                '___',
                '\(\d+ MB\)',
            ]
            std_qa = {
                # disable installation of Tosca (6) and Isight (7)
                "Isight\nEnter selection \(default: Next\):": '6\n7\n\n',
                "(?<!Isight)\nEnter selection \(default: Next\):": '',
                r"SIMULIA[0-9]*doc.*:": os.path.join(self.installdir, 'doc'),
                r"SimulationServices.*:": os.path.join(self.installdir, 'sim'),
                r"Choose the CODE installation directory.*:\n.*\n\n.*:": os.path.join(self.installdir, 'sim'),
                r"SIMULIA/CAE.*:": os.path.join(self.installdir, 'cae'),
                r"location of your Abaqus services \(solvers\).*(\n.*){8}:\s*": os.path.join(self.installdir, 'sim'),
                r"Default.*SIMULIA/Commands\]:\s*": os.path.join(self.installdir, 'Commands'),
                r"Default.*SIMULIA/CAE/plugins.*:\s*": os.path.join(self.installdir, 'plugins'),
                r"License Server 1\s*(\n.*){3}:": 'abaqusfea',  # bypass value for license server
                r"License Server . \(redundant\)\s*(\n.*){3}:": '',
                r"Please choose an action:": '1',
                r"SIMULIA/Tosca.*:": os.path.join(self.installdir, 'tosca'),
                r"location of your existing ANSA installation.*(\n.*){8}:": '',
                r"FLUENT Path.*(\n.*){7}:": '',
            }
            run_cmd_qa('./StartTUI.sh', qa, no_qa=no_qa, std_qa=std_qa, log_all=True, simple=True, maxhits=100)
        else:
            change_dir(self.builddir)
            if self.cfg['install_cmd'] is None:
                self.cfg['install_cmd'] = "%s/%s-%s/setup" % (self.builddir, self.name, self.version.split('-')[0])
                self.cfg['install_cmd'] += " -replay %s" % self.replayfile
                if LooseVersion(self.version) < LooseVersion("6.13"):
                    self.cfg['install_cmd'] += " -nosystemcheck"
            super(EB_ABAQUS, self).install_step()

        if LooseVersion(self.version) >= LooseVersion('2016'):
            # also install hot fixes (if any)
            hotfixes = [src for src in self.src if 'CFA' in src['name']]
            if hotfixes:
                # first install Part_3DEXP_SimulationServices hotfix(es)
                hotfix_dir = os.path.join(self.builddir, 'Part_3DEXP_SimulationServices.Linux64', '1', 'Software')
                change_dir(hotfix_dir)

                # SIMULIA_ComputeServices part
                subdirs = glob.glob('HF_SIMULIA_ComputeServices.HF*.Linux64')
                if len(subdirs) == 1:
                    subdir = subdirs[0]
                else:
                    raise EasyBuildError("Failed to find expected subdir for hotfix: %s", subdirs)

                cwd = change_dir(os.path.join(subdir, '1'))
                std_qa = {
                    "Enter selection \(default: Next\):": '',
                    "Choose the .*installation directory.*\n.*\n\n.*:": os.path.join(self.installdir, 'sim'),
                    "Enter selection \(default: Install\):": '',
                }
                run_cmd_qa('./StartTUI.sh', {}, std_qa=std_qa, log_all=True, simple=True, maxhits=100)

                # F_CAASIMULIAComputeServicesBuildTime part
                change_dir(cwd)
                subdirs = glob.glob('HF_CAASIMULIAComputeServicesBuildTime.HF*.Linux64')
                if len(subdirs) == 1:
                    subdir = subdirs[0]
                else:
                    raise EasyBuildError("Failed to find expected subdir for hotfix: %s", subdirs)

                change_dir(os.path.join(cwd, subdir, '1'))
                run_cmd_qa('./StartTUI.sh', {}, std_qa=std_qa, log_all=True, simple=True, maxhits=100)

                # next install Part_SIMULIA_Abaqus_CAE hotfix
                hotfix_dir = os.path.join(self.builddir, 'Part_SIMULIA_Abaqus_CAE.Linux64', '1', 'Software')
                change_dir(hotfix_dir)

                subdirs = glob.glob('SIMULIA_Abaqus_CAE.HF*.Linux64')
                if len(subdirs) == 1:
                    subdir = subdirs[0]
                else:
                    raise EasyBuildError("Failed to find expected subdir for hotfix: %s", subdirs)

                cwd = change_dir(os.path.join(subdir, '1'))
                std_qa = {
                    "Enter selection \(default: Next\):": '',
                    "Choose the .*installation directory.*\n.*\n\n.*:": os.path.join(self.installdir, 'cae'),
                    "Enter selection \(default: Install\):": '',
                    "Please choose an action:": '',
                }
                run_cmd_qa('./StartTUI.sh', {}, std_qa=std_qa, log_all=True, simple=True, maxhits=100)

    def sanity_check_step(self):
        """Custom sanity check for ABAQUS."""
        custom_paths = {
            'files': [os.path.join('Commands', 'abaqus')],
            'dirs': [],
        }
        custom_commands = []

        if LooseVersion(self.version) >= LooseVersion('2016'):
            custom_paths['dirs'].extend(['cae', 'Commands', 'doc', 'sim'])
            # 'all' also check license server, but lmstat is usually not available
            custom_commands.append("abaqus information=system")
        else:
            verparts = self.version.split('-')[0].split('.')
            custom_paths['dirs'].append('%s-%s' % ('.'.join(verparts[0:2]), verparts[2]))
            custom_commands.append("abaqus information=all")

        super(EB_ABAQUS, self).sanity_check_step(custom_paths=custom_paths, custom_commands=custom_commands)

    def make_module_req_guess(self):
        """Update PATH guesses for ABAQUS."""

        guesses = super(EB_ABAQUS, self).make_module_req_guess()
        guesses.update({
            'PATH': ['Commands'],
        })
        return guesses
