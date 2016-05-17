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
EasyBuild support for SuiteSparse, implemented as an easyblock

@author: Stijn De Weirdt (Ghent University)
@author: Dries Verdegem (Ghent University)
@author: Kenneth Hoste (Ghent University)
@author: Pieter De Baets (Ghent University)
@author: Jens Timmerman (Ghent University)
"""
import fileinput
import re
import os
import shutil
import sys
from distutils.version import LooseVersion

from easybuild.easyblocks.generic.configuremake import ConfigureMake
from easybuild.tools.build_log import EasyBuildError
from easybuild.tools.filetools import mkdir, write_file
from easybuild.tools.modules import get_software_root
from easybuild.tools.modules import get_software_libdir
from easybuild.tools.systemtools import get_shared_lib_ext


class EB_SuiteSparse(ConfigureMake):
    """Support for building SuiteSparse."""

    def __init__(self, *args, **kwargs):
        """Custom constructor for SuiteSparse easyblock, initialize custom class parameters."""
        super(EB_SuiteSparse, self).__init__(*args, **kwargs)
        self.config_name = 'UNKNOWN'

    def configure_step(self):
        """Configure build by patching UFconfig.mk or SuiteSparse_config.mk."""

        if LooseVersion(self.version) < LooseVersion('4.0'):
            self.config_name = 'UFconfig'
        else:
            self.config_name = 'SuiteSparse_config'

        cfgvars = {
            'CC': os.getenv('MPICC'),
            'CFLAGS': os.getenv('CFLAGS'),
            'CXX': os.getenv('MPICXX'),
            'F77': os.getenv('MPIF77'),
            'F77FLAGS': os.getenv('F77FLAGS'),
        }

        # Set BLAS and LAPACK libraries as specified in SuiteSparse README.txt
        self.cfg.update('buildopts', 'BLAS="%s"' % os.getenv('LIBBLAS_MT'))
        self.cfg.update('buildopts', 'LAPACK="%s"' % os.getenv('LIBLAPACK_MT'))

        # Get METIS or ParMETIS settings
        metis = get_software_root('METIS')
        parmetis = get_software_root('ParMETIS')
        if parmetis:
            metis_path = parmetis
            metis_include = os.path.join(parmetis, 'include')
            metis_libs = os.path.join(parmetis, get_software_libdir('ParMETIS'), 'libmetis.a')

        elif metis:
            metis_path = metis
            metis_include = os.path.join(metis, 'include')
            metis_libs = os.path.join(metis, get_software_libdir('METIS'), 'libmetis.a')

        else:
            raise EasyBuildError("Neither METIS or ParMETIS module loaded.")

        if LooseVersion(self.version) >= LooseVersion('4.5.1'):
            cfgvars.update({
                'MY_METIS_LIB': metis_libs,
                'MY_METIS_INC': metis_include,
            })
        else:
            cfgvars.update({
                'METIS_PATH': metis_path,
                'METIS': metis_libs,
            })

        # patch file
        fp = os.path.join(self.cfg['start_dir'], self.config_name, '%s.mk' % self.config_name)

        try:
            for line in fileinput.input(fp, inplace=1, backup='.orig'):
                for (var, val) in cfgvars.items():
                    orig_line = line
                    # for variables in cfgvars, substiture lines assignment 
                    # in the file, whatever they are, by assignments to the
                    # values in cfgvars
                    line = re.sub(r"^\s*(%s\s*=\s*).*\n$" % var,
                                  r"\1 %s # patched by EasyBuild\n" % val,
                                  line)
                    if line != orig_line:
                        cfgvars.pop(var)
                sys.stdout.write(line)
        except IOError, err:
            raise EasyBuildError("Failed to patch %s in: %s", fp, err)

        # add remaining entries at the end
        if cfgvars:
            cfgtxt = '# lines below added automatically by EasyBuild\n'
            cfgtxt += '\n'.join(["%s = %s" % (var, val) for (var, val) in cfgvars.items()])
            write_file(fp, cfgtxt, append=True)

    def install_step(self):
        """Install by copying the contents of the builddir to the installdir (preserving permissions)"""
        for x in os.listdir(self.cfg['start_dir']):
            src = os.path.join(self.cfg['start_dir'], x)
            dst = os.path.join(self.installdir, x)
            try:
                if os.path.isdir(src):
                    shutil.copytree(src, dst)
                    # symlink 
                    # - dst/Lib to dst/lib
                    # - dst/Include to dst/include
                    for c in ['Lib', 'Include']:
                        nsrc = os.path.join(dst, c)
                        ndst = os.path.join(dst, c.lower())
                        if os.path.exists(nsrc):
                            os.symlink(nsrc, ndst)
                else:
                    shutil.copy2(src, dst)
            except OSError, err:
                raise EasyBuildError("Copying src %s to dst %s failed: %s", src, dst, err)

        # some extra symlinks are necessary for UMFPACK to work.
        paths = [
            os.path.join('AMD', 'include', 'amd.h'),
            os.path.join('AMD' ,'include' ,'amd_internal.h'),
            os.path.join(self.config_name, '%s.h' % self.config_name),
            os.path.join('AMD', 'lib', 'libamd.a')
        ]
        for path in paths:
            src = os.path.join(self.installdir, path)
            dn = path.split(os.path.sep)[-2]
            fn = path.split(os.path.sep)[-1]
            dstdir = os.path.join(self.installdir, 'UMFPACK', dn)
            mkdir(dstdir)
            if os.path.exists(src):
                try:
                    os.symlink(src, os.path.join(dstdir, fn))
                except OSError, err:
                    raise EasyBuildError("Failed to make symbolic link from %s to %s: %s", src, dst, err)

    def make_module_req_guess(self):
        """
        Extra path to consider for module file:
        * add config dir and include to $CPATH so include files are found
        * add UMFPACK and AMD library, and lib dirs to $LD_LIBRARY_PATH
        """

        guesses = super(EB_SuiteSparse, self).make_module_req_guess()

        # Previous versions of SuiteSparse used specific directories for includes and libraries
        if LooseVersion(self.version) < LooseVersion('4.5'):
            include_dirs = [self.config_name]
            ld_library_path = ['AMD/lib', 'BTF/lib', 'CAMD/lib', 'CCOLAMD/lib', 'CHOLAMD/lib', 'CHOLMOD/lib',
                               'COLAMD/lib/', 'CSparse/lib', 'CXSparse/lib', 'KLU/lib', 'LDL/lib', 'RBio/lib',
                               'UMFPACK/lib', self.config_name]

            guesses['CPATH'].extend(include_dirs)
            guesses['LD_LIBRARY_PATH'].extend(ld_library_path)
            guesses['LIBRARY_PATH'].extend(ld_library_path)

        return guesses

    def sanity_check_step(self):
        """Custom sanity check for SuiteSparse."""

        # Make sure that SuiteSparse did NOT compile its own Metis
        if os.path.exists(os.path.join(self.installdir, 'lib', 'libmetis.%s' % get_shared_lib_ext())):
            raise EasyBuildError("SuiteSparse has compiled its own Metis. This will conflict with the Metis build."
                                 " The SuiteSparse EasyBlock need to be updated!")

        libnames = ['AMD', 'BTF', 'CAMD', 'CCOLAMD', 'CHOLMOD', 'COLAMD', 'CXSparse', 'KLU',
                    'LDL', 'RBio', 'SPQR', 'UMFPACK']
        libs = [os.path.join(x, 'lib', 'lib%s.a' % x.lower()) for x in libnames]

        if LooseVersion(self.version) < LooseVersion('4.0'):
            csparse_dir = 'CSparse3'
        else:
            csparse_dir = 'CSparse'
        libs.append(os.path.join(csparse_dir, 'lib', 'libcsparse.a'))

        # Latest version of SuiteSparse also compiles shared library and put them in 'lib'
        shlib_ext = get_shared_lib_ext()
        if LooseVersion(self.version) >= LooseVersion('4.5.1'):
            libs += [os.path.join('lib', 'lib%s.%s' % (l.lower(), shlib_ext)) for l in libnames]

        custom_paths = {
            'files': libs,
            'dirs': ['MATLAB_Tools'],
        }

        super(EB_SuiteSparse, self).sanity_check_step(custom_paths=custom_paths)
