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
EasyBuild support for building and installing QScintilla, implemented as an easyblock

author: Kenneth Hoste (HPC-UGent)
"""
import os
from distutils.version import LooseVersion

from easybuild.easyblocks.generic.configuremake import ConfigureMake
from easybuild.easyblocks.generic.pythonpackage import det_pylibdir
from easybuild.tools.build_log import EasyBuildError
from easybuild.tools.filetools import apply_regex_substitutions, mkdir, symlink, write_file
from easybuild.tools.modules import get_software_root
from easybuild.tools.run import run_cmd
from easybuild.tools.systemtools import get_shared_lib_ext


class EB_QScintilla(ConfigureMake):
    """Support for building/installing QScintilla."""

    def configure_step(self):
        """Custom configuration procedure for QScintilla."""

        srcdir = os.path.join(self.cfg['start_dir'], 'Qt4Qt5')
        try:
            os.chdir(srcdir)
        except OSError as err:
            raise EasyBuildError("Failed to change to %s: %s", srcdir, err)

        # replace template values for install locations in qscintilla.pro configuration file
        regex_subs = [
            (r'\$\$\[QT_HOST_DATA\]', os.path.join(self.installdir, 'data')),
            (r'\$\$\[QT_INSTALL_DATA\]', os.path.join(self.installdir, 'data')),
            (r'\$\$\[QT_INSTALL_HEADERS\]', os.path.join(self.installdir, 'include')),
            (r'\$\$\[QT_INSTALL_LIBS\]', os.path.join(self.installdir, 'lib')),
            (r'\$\$\[QT_INSTALL_TRANSLATIONS\]', os.path.join(self.installdir, 'trans')),
        ]
        apply_regex_substitutions('qscintilla.pro', regex_subs) 

        run_cmd("qmake qscintilla.pro")

    def build_step(self):
        """Custom build procedure for QScintilla."""

        # make sure that $CXXFLAGS is being passed down
        self.cfg.update('buildopts', 'CXXFLAGS="$CXXFLAGS \$(DEFINES)"')

        super(EB_QScintilla, self).build_step()

    def install_step(self):
        """Custom install procedure for QScintilla."""
        
        super(EB_QScintilla, self).install_step()

        # also install Python bindings if Python is included as a dependency
        python = get_software_root('Python')
        if python:
            pydir = os.path.join(self.cfg['start_dir'], 'Python')
            try:
                os.chdir(pydir)
            except OSError as err:
                raise EasyBuildError("Failed to change to %s: %s", pydir, err)

            # apparently this directory has to be there
            qsci_sipdir = os.path.join(self.installdir, 'share', 'sip', 'PyQt4')
            mkdir(qsci_sipdir, parents=True)

            pylibdir = os.path.join(det_pylibdir(), 'PyQt4')

            pyqt = get_software_root('PyQt')
            if pyqt is None:
                raise EasyBuildError("Failed to determine PyQt installation prefix, PyQt not included as dependency?")

            cfgopts = [
                '--destdir %s' % os.path.join(self.installdir, pylibdir),
                '--qsci-sipdir %s' % qsci_sipdir,
                '--qsci-incdir %s' % os.path.join(self.installdir, 'include'),
                '--qsci-libdir %s' % os.path.join(self.installdir, 'lib'),
                '--pyqt-sipdir %s' % os.path.join(pyqt, 'share', 'sip', 'PyQt4'),
                '--apidir %s' % os.path.join(self.installdir, 'qsci', 'api', 'python'),
                '--no-stubs',
            ]
            run_cmd("python configure.py %s" % ' '.join(cfgopts))

            super(EB_QScintilla, self).build_step()
            super(EB_QScintilla, self).install_step()

            target_dir = os.path.join(self.installdir, pylibdir)
            pyqt_pylibdir = os.path.join(pyqt, pylibdir)
            try:
                os.chdir(target_dir)
                for entry in [x for x in os.listdir(pyqt_pylibdir) if not x.startswith('__init__.py')]:
                    symlink(os.path.join(pyqt_pylibdir, entry), os.path.join(target_dir, entry))
            except OSError as err:
                raise EasyBuildError("Failed to symlink PyQt Python bindings in %s: %s", target_dir, err)

            # also requires empty __init__.py file to ensure Python modules can be imported from this location
            write_file(os.path.join(target_dir, '__init__.py'), '')

    def sanity_check_step(self):
        """Custom sanity check for QScintilla."""

        if LooseVersion(self.version) >= LooseVersion('2.10'):
            qsci_lib = 'libqscintilla2_qt4'
        else:
            qsci_lib = 'libqscintilla2'

        custom_paths = {
            'files': [os.path.join('lib', qsci_lib + '.' + get_shared_lib_ext())],
            'dirs': ['data', os.path.join('include', 'Qsci'), os.path.join(det_pylibdir(), 'PyQt4'),
                     os.path.join('qsci', 'api', 'python'), os.path.join('share', 'sip', 'PyQt4'), 'trans'],
        }
        custom_commands = ["python -c 'import PyQt4.Qsci'"]

        super(EB_QScintilla, self).sanity_check_step(custom_paths=custom_paths, custom_commands=custom_commands)

    def make_module_extra(self):
        """Custom extra module file entries for QScintilla."""
        txt = super(EB_QScintilla, self).make_module_extra()
        txt += self.module_generator.prepend_paths('PYTHONPATH', [det_pylibdir()])
        return txt
