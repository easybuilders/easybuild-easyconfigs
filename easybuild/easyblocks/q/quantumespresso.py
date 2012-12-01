##
# Copyright 2009-2012 Ghent University
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
EasyBuild support for QuantumESPRESSO, implemented as an easyblock
"""
import os
import re
import shutil
import tempfile

from easybuild.easyblocks.generic.configuremake import ConfigureMake

class QuantumESPRESSO(ConfigureMake):

    def configure_step(self):
        oldextralibpath = os.path.join(self.builddir, 'install')
        newextralibpath = os.path.join(self.cfg[start_dir], 'install')
        extralibs = os.listdir(oldextralibpath)
        try:
            for lib in extralibs:
                shutil.copy2(os.path.join(oldextralibpath, lib), newextralibpath)
        except Exception, err:
            self.log.error("Failed to copy %s to %s, %s" % (lib, newextralibpath, err))

        ConfigureMake.configure(self)

        if self.toolchain().name == 'ictce':
            makesysfile = os.path.join(self.cfg[start_dir], 'make.sys')

            mkllib = "%s/lib/em64t" % os.environ['SOFTROOTIMKL']

            regopenmp = re.compile(r"openmp")
            regscal = re.compile(r"scalapack")

            makesysregdflags = re.compile(r"^DFLAGS\s*=.*$", re.M)
            makesysrepldflags = "DFLAGS = -D__INTEL -D__FFTW3 -D__MPI -D__PARA"
            if regopenmp.search(self.cfg[configopts]):
                makesysrepldflags += " -D__OPENMP"
            if regscal.search(self.cfg[configopts]):
                makesysrepldflags += " -D__SCALAPACK"

            makesysregflags = re.compile(r"^(?:C|F90|F)FLAGS.*$", re.M)
            makesysreplflags = "\g<0>"
            if regopenmp.search(self.cfg[configopts]):
                makesysreplflags += " -openmp"

            makesysregblas = re.compile(r"^BLAS_LIBS\s*=.*$", re.M)
            makesysreplblas = "BLAS_LIBS = %s/libmkl_em64t.a\n" % (mkllib)

            makesysregscal = re.compile(r"^SCALAPACK_LIBS\s*=.*$", re.M)
            makesysreplscal = "SCALAPACK_LIBS = %s/libmkl_scalapack.a %s/libmkl_blacs_lp64.a\n" % (mkllib, mkllib)

            makesysreglibs = re.compile(r"^LD_LIBS\s*=.*$", re.M)
            makesysrepllibs = "LD_LIBS = -liomp5 -lpthread"

            try:
                f = open(makesysfile, 'r')
                origcontent = f.read()
                f.close()
            except Exception, err:
                self.log.error("Can't read from file %s: %s" % (makesysfile, err))

            try:
                os.remove(makesysfile)
            except Exception, err:
                self.log.error("It is not possible to remove the old version of %s" % makesysfile)

            try:
                f = open(makesysfile, 'w')
                origcontent = makesysregscal.sub(makesysreplscal, origcontent)
                origcontent = makesysreglibs.sub(makesysrepllibs, origcontent)
                origcontent = makesysregblas.sub(makesysreplblas, origcontent)
                origcontent = makesysregdflags.sub(makesysrepldflags, origcontent)
                origcontent = makesysregflags.sub(makesysreplflags, origcontent)
                f.write(origcontent)
                f.close()
                self.log.info("New version of file %s successfully written" % makesysfile)
            except Exception, err:
                self.log.error("Can't write to file %s: %s" % (makesysfile, err))

    def install_step(self):
        try:
            shutil.copytree(os.path.join(self.cfg[start_dir], 'bin'), os.path.join(self.installdir, 'bin'))
        except Exception, err:
            self.log.error("Something went wrong during bin dir copying to installdir: %s" % err)

    def sanity_check_step(self):

        custom_paths = {
                        'files': [],
                        'dirs': ["bin"]
                       }

        ConfigureMake.sanity_check_step(self, custom_paths=custom_paths)
