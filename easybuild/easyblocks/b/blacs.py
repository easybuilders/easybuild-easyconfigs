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
EasyBuild support for building and installing BLACS, implemented as an easyblock

@author: Stijn De Weirdt (Ghent University)
@author: Dries Verdegem (Ghent University)
@author: Kenneth Hoste (Ghent University)
@author: Pieter De Baets (Ghent University)
@author: Jens Timmerman (Ghent University)
"""

import glob
import re
import os
import shutil

from easybuild.easyblocks.generic.configuremake import ConfigureMake
from easybuild.tools.build_log import EasyBuildError
from easybuild.tools.run import run_cmd


# also used by ScaLAPACK
def det_interface(log, path):
    """Determine interface through 'xintface' heuristic tool"""

    (out, _) = run_cmd(os.path.join(path,"xintface"), log_all=True, simple=False)

    intregexp = re.compile(".*INTFACE\s*=\s*-D(\S+)\s*")
    res = intregexp.search(out)
    if res:
        return res.group(1)
    else:
        raise EasyBuildError("Failed to determine interface, output for xintface: %s", out)


class EB_BLACS(ConfigureMake):
    """
    Support for building/installing BLACS
    - configure: symlink BMAKES/Bmake.MPI-LINUX to Bmake.inc
    - make install: copy files
    """

    def configure_step(self):
        """Configure BLACS build by copying Bmake.inc file."""

        src = os.path.join(self.cfg['start_dir'], 'BMAKES', 'Bmake.MPI-LINUX')
        dest = os.path.join(self.cfg['start_dir'], 'Bmake.inc')

        if not os.path.isfile(src):
            raise EasyBuildError("Can't find source file %s", src)

        if os.path.exists(dest):
            raise EasyBuildError("Destination file %s exists", dest)

        try:
            shutil.copy(src, dest)
        except OSError, err:
            raise EasyBuildError("Copying %s to %s failed: %s", src, dest, err)

    def build_step(self):
        """Build BLACS using build_step, after figuring out the make options based on the heuristic tools available."""

        opts = {
                'mpicc': "%s %s" % (os.getenv('MPICC'), os.getenv('CFLAGS')),
                'mpif77': "%s %s" % (os.getenv('MPIF77'), os.getenv('FFLAGS')),
                'f77': os.getenv('F77'),
                'cc': os.getenv('CC'),
                'builddir': os.getcwd(),
                'mpidir': os.path.dirname(os.getenv('MPI_LIB_DIR')),
               }

        # determine interface and transcomm settings
        comm = ''
        interface = 'UNKNOWN'
        try:
            cwd = os.getcwd()
            os.chdir('INSTALL')

            # need to build
            cmd = "make"
            cmd += " CC='%(mpicc)s' F77='%(mpif77)s' MPIdir=%(mpidir)s" \
                   " MPILIB='' BTOPdir=%(builddir)s INTERFACE=NONE" % opts

            # determine interface using xintface
            run_cmd("%s xintface" % cmd, log_all=True, simple=True)

            interface = det_interface(self.log, "./EXE")

            # try and determine transcomm using xtc_CsameF77 and xtc_UseMpich
            if not comm:

                run_cmd("%s xtc_CsameF77" % cmd, log_all=True, simple=True)

                (out, _) = run_cmd(self.toolchain.mpi_cmd_for("./EXE/xtc_CsameF77", 2), log_all=True, simple=False)

                # get rid of first two lines, that inform about how to use this tool
                out = '\n'.join(out.split('\n')[2:])

                notregexp = re.compile("_NOT_")

                if not notregexp.search(out):
                    # if it doesn't say '_NOT_', set it
                    comm = "TRANSCOMM='-DCSameF77'"

                else:
                    (_, ec) = run_cmd("%s xtc_UseMpich" % cmd, log_all=False, log_ok=False, simple=False)
                    if ec == 0:

                        (out, _) = run_cmd(self.toolchain.mpi_cmd_for("./EXE/xtc_UseMpich", 2), log_all=True, simple=False)

                        if not notregexp.search(out):

                            commregexp = re.compile('Set TRANSCOMM\s*=\s*(.*)$')

                            res = commregexp.search(out)
                            if res:
                                # found how to set TRANSCOMM, so set it
                                comm = "TRANSCOMM='%s'" % res.group(1)
                            else:
                                # no match, set empty TRANSCOMM
                                comm = "TRANSCOMM=''"
                    else:
                        # if it fails to compile, set empty TRANSCOMM
                        comm = "TRANSCOMM=''"

            os.chdir(cwd)
        except OSError, err:
            raise EasyBuildError("Failed to determine interface and transcomm settings: %s", err)

        opts.update({
                     'comm': comm,
                     'int': interface,
                    })

        add_makeopts = ' MPICC="%(mpicc)s" MPIF77="%(mpif77)s" %(comm)s ' % opts
        add_makeopts += ' INTERFACE=%(int)s MPIdir=%(mpidir)s BTOPdir=%(builddir)s mpi ' % opts

        self.cfg.update('buildopts', add_makeopts)

        super(EB_BLACS, self).build_step()

    def install_step(self):
        """Install by copying files to install dir."""

        # include files and libraries
        for (srcdir, destdir, ext) in [
                                       (os.path.join("SRC", "MPI"), "include", ".h"),  # include files
                                       ("LIB", "lib", ".a"),  # libraries
                                       ]:

            src = os.path.join(self.cfg['start_dir'], srcdir)
            dest = os.path.join(self.installdir, destdir)

            try:
                os.makedirs(dest)
                os.chdir(src)

                for lib in glob.glob('*%s' % ext):

                    # copy file
                    shutil.copy2(os.path.join(src, lib), dest)

                    self.log.debug("Copied %s to %s" % (lib, dest))

                    if destdir == 'lib':
                        # create symlink with more standard name for libraries
                        symlink_name = "lib%s.a" % lib.split('_')[0]
                        os.symlink(os.path.join(dest, lib), os.path.join(dest, symlink_name))
                        self.log.debug("Symlinked %s/%s to %s" % (dest, lib, symlink_name))

            except OSError, err:
                raise EasyBuildError("Copying %s/*.%s to installation dir %s failed: %s", src, ext, dest, err)

        # utilities
        src = os.path.join(self.cfg['start_dir'], 'INSTALL', 'EXE', 'xintface')
        dest = os.path.join(self.installdir, 'bin')

        try:
            os.makedirs(dest)

            shutil.copy2(src, dest)

            self.log.debug("Copied %s to %s" % (src, dest))

        except OSError, err:
            raise EasyBuildError("Copying %s to installation dir %s failed: %s", src, dest, err)

    def sanity_check_step(self):
        """Custom sanity check for BLACS."""

        custom_paths = {
                        'files': [fil for filptrn in ["blacs", "blacsCinit", "blacsF77init"]
                                      for fil in ["lib/lib%s.a" % filptrn,
                                                  "lib/%s_MPI-LINUX-0.a" % filptrn]] +
                                 ["bin/xintface"],
                        'dirs': []
                       }

        super(EB_BLACS, self).sanity_check_step(custom_paths=custom_paths)
