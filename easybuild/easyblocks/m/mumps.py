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
EasyBuild support for building and installing MUMPS, implemented as an easyblock

@author: Stijn De Weirdt (Ghent University)
@author: Dries Verdegem (Ghent University)
@author: Kenneth Hoste (Ghent University)
@author: Pieter De Baets (Ghent University)
@author: Jens Timmerman (Ghent University)
"""

import os
import shutil
from distutils.version import LooseVersion

import easybuild.tools.toolchain as toolchain
from easybuild.easyblocks.generic.configuremake import ConfigureMake
from easybuild.tools import toolchain
from easybuild.tools.build_log import EasyBuildError
from easybuild.tools.modules import get_software_root


class EB_MUMPS(ConfigureMake):
    """Support for building/installing MUMPS."""

    def configure_step(self):
        """Configure MUMPS build by copying right Makefile.inc template."""

        # pick a Makefile.inc template based on compiler family and MPI enabled
        if self.toolchain.options.get('usempi', None):
            make_inc_suff = 'PAR'
        else:
            make_inc_suff = 'SEQ'

        # select Makefile.inc template and prepare compiler specific compiler flags
        comp_fam = self.toolchain.comp_family()
        if comp_fam == toolchain.INTELCOMP:  #@UndefinedVariable
            make_inc_templ = 'Makefile.INTEL.%s'
            optf = "-Dintel_ -DALLOW_NON_INIT -nofor-main"
            optl = "-nofor-main"
        elif comp_fam == toolchain.GCC:  #@UndefinedVariable
            if LooseVersion(self.version) >= LooseVersion('5.0.0'):
                make_inc_templ = 'Makefile.debian.%s'
            else:
                make_inc_templ = 'Makefile.gfortran.%s'

            optf = "-DALLOW_NON_INIT"
            optl = ""
        else:
            raise EasyBuildError("Unknown compiler family, don't know to prepare for building with specified toolchain.")

        # copy selected Makefile.inc template
        try:
            src = os.path.join(self.cfg['start_dir'], 'Make.inc', make_inc_templ % make_inc_suff)
            dst = os.path.join(self.cfg['start_dir'], 'Makefile.inc')
            shutil.copy2(src, dst)
            self.log.debug("Successfully copied Makefile.inc to builddir.")
        except OSError, err:
            raise EasyBuildError("Copying Makefile.inc to builddir failed: %s", err)

        # check whether dependencies are available, and prepare
        scotch = get_software_root('SCOTCH')
        if not scotch:
            raise EasyBuildError("SCOTCH dependency not available.")

        metis = get_software_root('METIS')
        parmetis = get_software_root('ParMETIS')
        if parmetis:
            lmetisdir = "$EBROOTPARMETIS"
            lmetis= "-L$EBROOTPARMETIS -lparmetis -lmetis"
            dmetis = "-Dparmetis"
        elif metis:
            lmetisdir = "$EBROOTMETIS"
            lmetis= "-L$EBROOTMETIS -lmetis"
            dmetis = "-Dmetis"
        else:
            raise EasyBuildError("METIS or ParMETIS must be available as dependency.")

        # set Make options
        mumps_make_opts = {
            'SCOTCHDIR': "$EBROOTSCOTCH",
            'LSCOTCH': "-L$EBROOTSCOTCH/lib -lptesmumps -lptscotch -lptscotcherr -lesmumps -lscotch -lscotcherr",
            'ISCOTCH': "-I$EBROOTSCOTCH/include",
            'LMETISDIR': lmetisdir,
            'LMETIS': lmetis,
            'IMETIS': "-I%s/include" % lmetisdir,
            'ORDERINGSF': "-Dpord -Dptscotch %s" % dmetis,
            'CC': "$MPICC",
            'FC': "$MPIF77",
            'FL': "$MPIF77",
            'SCALAP': "-L$SCALAPACK_LIB_DIR $LIBSCALAPACK",
            'INCPAR': "",
            'LIBPAR': "-L$SCALAPACK_LIB_DIR $LIBSCALAPACK",
            'INCSEQ': "",
            'LIBSEQ': "",
            'LIBBLAS': "-L$BLAS_LIB_DIR $LIBBLAS",
            'LIBOTHERS': "$LIBS",
            'OPTF': "$FFLAGS %s" % optf,
            'OPTL': "$LDFLAGS %s" % optl,
            'OPTC': "$CFLAGS",
        }
        for (key, val) in mumps_make_opts.items():
            self.cfg.update('buildopts', '%s="%s"' % (key, val))

    def install_step(self):
        """Install MUMPS by copying files to install dir."""
        try:
            for path in ["include", "lib", "doc"]:
                src = os.path.join(self.cfg['start_dir'], path)
                dst = os.path.join(self.installdir, path)
                shutil.copytree(src, dst)
        except OSError, err:
            raise EasyBuildError("Copying %s to installation dir %s failed: %s", src, dst, err)

    def sanity_check_step(self):
        """Custom sanity check for MUMPS."""
        custom_paths = {
            'files': ["include/%s%s.h" % (x, y) for x in ["c", "d", "s", "z"]
                                                for y in ["mumps_c", "mumps_root", "mumps_struc"]] +
                     ["include/mumps_compat.h", "include/mumps_c_types.h"] +
                     ["lib/lib%smumps.a" % x for x in ["c", "d", "s", "z"]] +
                     ["lib/libmumps_common.a", "lib/libpord.a"],
            'dirs': [],
        }

        super(EB_MUMPS, self).sanity_check_step(custom_paths=custom_paths)

