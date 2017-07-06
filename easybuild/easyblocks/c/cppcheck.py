##
# Copyright 2016 Forschungszentrum Juelich GmbH
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
@author: Damian Alvarez (Forschungszentrum Juelich GmbH)
"""
import os
import shutil

from easybuild.easyblocks.generic.configuremake import ConfigureMake
from easybuild.framework.easyconfig import CUSTOM
from easybuild.tools.build_log import EasyBuildError
from easybuild.tools.run import run_cmd


class EB_cppcheck(ConfigureMake):
    """
    EasyBlock to install cppcheck
    """
    
    @staticmethod
    def extra_options(extra_vars=None):
        """
        Define if we are using rules or not, and if we are building the GUI
        """
        extra = {
            'have_rules': [False, "Use rules", CUSTOM],
            'build_gui': [False, "Build GUI", CUSTOM],
        }
        if extra_vars is None:
            extra_vars = {}
        extra.update(extra_vars)
        return ConfigureMake.extra_options(extra_vars=extra)

    def configure_step(self):
        """
        Run qmake on the GUI, if necessary
        """
        if self.cfg['build_gui']:
            cmd = 'qmake QMAKE_CXX="$CXX" QMAKE_LINK="$CXX"'

            if self.cfg['have_rules']:
                cmd = ' '.join([cmd, 'HAVE_RULES=yes'])
            
            gui_dir = os.path.join(self.cfg['start_dir'], 'gui')

            try:
                os.chdir(gui_dir)
                run_cmd(cmd, log_all=True, simple=True)
                os.chdir(self.cfg['start_dir'])
            except OSError as err:
                raise EasyBuildError("Moving to %s and configure the GUI build failed: %s", gui_dir, err)

        else:
            self.log.debug("Configuration of the GUI skipped")

    def build_step(self, verbose=False):
        """
        Compile cppcheck with make and cppcheck-gui with qmake and make 
        """
        self.cfg.update('buildopts', 'CFGDIR=%(installdir)s/cfg')
        
        if self.cfg['have_rules']:
            self.cfg.update('buildopts', 'HAVE_RULES=yes')

        super(EB_cppcheck, self).build_step(verbose=verbose)
        
        if self.cfg['build_gui']:
            super(EB_cppcheck, self).build_step(verbose=verbose, path='gui')

    def install_step(self):
        """
        Install cppcheck with make install and cppcheck-gui copying the file
        """
        self.cfg.update('installopts', 'DESTDIR=%(installdir)s/ PREFIX="" CFGDIR=cfg')
        
        super(EB_cppcheck, self).install_step()
       
        # The GUI doesn't have make install, so we copy it manually
        if self.cfg['build_gui']:
            filepath = os.path.join(self.cfg['start_dir'], 'gui/', 'cppcheck-gui')

            try:
                # make sure we're (still) in the start dir
                os.chdir(self.cfg['start_dir'])

                # Perform the copy
                target_dest = os.path.join(self.installdir, 'bin')
                if os.path.isfile(filepath):
                    self.log.debug("Copying file %s to %s" % (filepath, target_dest))
                    shutil.copy2(filepath, target_dest)
                else:
                    raise EasyBuildError("Can't copy non-existing file %s to %s", filepath, target_dest)
                
                # Create cfg symlink. It shouldn't be necessary, but cppcheck-gui complains otherwise
                # unless called with --data-dir
                src = os.path.join(self.installdir, 'cfg')
                dst = os.path.join(self.installdir, 'bin/cfg')
                self.log.debug("Creating symlink %s to %s" % (src, dst))
                os.symlink(src, dst)

            except OSError as err:
                raise EasyBuildError("Copying %s to installation dir failed: %s", filepath, err)

    def sanity_check_step(self):
        """
        Custom sanity check for cppcheck.
        """
        custom_paths = {
            'files': ['bin/cppcheck'],
            'dirs': []
        }

        if self.cfg['build_gui']:
            custom_paths['files'].append('bin/cppcheck-gui')
            custom_paths['dirs'].append('bin/cfg')

        super(EB_cppcheck, self).sanity_check_step(custom_paths=custom_paths)
