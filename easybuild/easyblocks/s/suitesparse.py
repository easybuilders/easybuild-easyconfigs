##
# Copyright 2009-2013 Ghent University
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
from easybuild.tools.filetools import mkdir
from easybuild.tools.modules import get_software_root


class EB_SuiteSparse(ConfigureMake):
    """Support for building SuiteSparse."""

    def __init__(self, *args, **kwargs):
        """Custom constructor for SuiteSparse easyblock, initialize custom class parameters."""
        super(EB_SuiteSparse, self).__init__(*args, **kwargs)
        self.config_name = None

    def configure_step(self):
        """Configure build by patching UFconfig.mk or SuiteSparse_config.mk."""

        if LooseVersion(self.version) < LooseVersion('4.0'):
            self.config_name = 'UFconfig'
        else:
            self.config_name = 'SuiteSparse_config'

        fp = os.path.join(self.cfg['start_dir'], self.config_name, '%s.mk' % self.config_name)

        cfgvars = {
            'CC': os.getenv('MPICC'),
            'CFLAGS': os.getenv('CFLAGS'),
            'CXX': os.getenv('MPICXX'),
            'F77': os.getenv('MPIF77'),
            'F77FLAGS': os.getenv('F77FLAGS'),
            'BLAS': os.getenv('LIBBLAS_MT'),
            'LAPACK': os.getenv('LIBLAPACK_MT'),
        }

        metis = get_software_root('METIS')
        parmetis = get_software_root('ParMETIS')
        if parmetis:
            metis_path = parmetis
            metis_libs = ' '.join([
                os.path.join(parmetis, 'lib', 'libparmetis.a'),
                os.path.join(parmetis, 'lib', 'metis.a'),
            ])
        elif metis:
            metis_path = metis
            metis_libs = os.path.join(metis, 'lib', 'metis.a')
        else:
            self.log.error("Neither METIS or ParMETIS module loaded.")

        cfgvars.update({
            'METIS_PATH': metis_path,
            'METIS': metis_libs,
        })

        # patch file
        try:
            for line in fileinput.input(fp, inplace=1, backup='.orig'):
                for (k, v) in cfgvars.items():
                    line = re.sub(r"^(%s\s*=\s*).*$" % k, r"\1 %s # patched by EasyBuild" % v, line)
                    if k in line:
                        cfgvars.pop(k)
                sys.stdout.write(line)
        except IOError, err:
            self.log.error("Failed to patch %s in: %s" % (fp, err))

        # add remaining entries at the end
        if cfgvars:
            try:
                f = open(fp, "a")
                f.write("# lines below added automatically by EasyBuild")
                for (k, v) in cfgvars.items():
                    f.write("%s = %s\n" % (k,v))
                f.close()
            except IOError, err:
                self.log.error("Failed to complete %s: %s" % (fp, err))

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
            except:
                self.log.exception("Copying src %s to dst %s failed" % (src, dst))

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
                except Exception, err:
                    self.log.error("Failed to make symbolic link from %s to %s: %s" % (src, dst, err))

    def make_module_req_guess(self):
        """Add config dir to CPATH so include file is found."""
        guesses = super(EB_SuiteSparse, self).make_module_req_guess()
        guesses.update({'CPATH': [self.config_name]})
        return guesses

    def sanity_check_step(self):
        """Custom sanity check for SuiteSparse."""

        if LooseVersion(self.version) < LooseVersion('4.0'):
            csparse_dir = 'CSparse3'
        else:
            csparse_dir = 'CSparse'

        custom_paths = {
            'files': [os.path.join(x, 'lib', 'lib%s.a' % x.lower()) for x in ["AMD", "BTF", "CAMD", "CCOLAMD", "CHOLMOD",
                                                                              "COLAMD", "CXSparse", "KLU", "LDL", "RBio",
                                                                              "SPQR", "UMFPACK"]] +
                     [os.path.join(csparse_dir, 'lib', 'libcsparse.a')],
            'dirs': ["MATLAB_Tools"],
        }

        super(EB_SuiteSparse, self).sanity_check_step(custom_paths=custom_paths)
