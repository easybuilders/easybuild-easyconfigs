##
# Copyright 2009-2012 Stijn De Weirdt, Dries Verdegem, Kenneth Hoste, Pieter De Baets, Jens Timmerman
#
# This file is part of EasyBuild,
# originally created by the HPC team of the University of Ghent (http://ugent.be/hpc).
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
from easybuild.framework.application import Application
from easybuild.tools.filetools import run_cmd
import os
import shutil

class SuiteSparse(Application):

    def configure(self):
        pass

    def make(self):
        cmd = 'make'

        run_cmd(cmd, log_all=True, simple=True)

    def make_install(self):
        """
        Just copy the contents of the builddir to the installdir
        - keep permissions with copy2 !!
        """
        for x in os.listdir(self.getcfg('startfrom')):
            src = os.path.join(self.getcfg('startfrom'), x)
            dst = os.path.join(self.installdir, x)
            try:
                if os.path.isdir(src):
                    shutil.copytree(src, dst)
                    #symlink 
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

        # Some extra symlinks are necessary for UMFPACK to work.
        for f in ['AMD/include/amd.h', 'AMD/include/amd_internal.h', 'UFconfig/UFconfig.h']:
            src = os.path.join(self.installdir, f)
            dst = os.path.join(self.installdir, 'UMFPACK', 'include', f.split('/')[-1])
            if os.path.exists(src):
                try: os.symlink(src, dst)
                except Exception, err:
                    self.log.error("Failed to make symbolic link from %s to %s: %s" % (src, dst, err))

        for f in ['AMD/lib/libamd.a']:
            src = os.path.join(self.installdir, f)
            dst = os.path.join(self.installdir, 'UMFPACK', 'lib', f.split('/')[-1])
            if os.path.exists(src):
                try: os.symlink(src, dst)
                except Exception, err:
                    self.log.error("Failed to make symbolic link from %s to %s: %s" % (src, dst, err))

    def sanitycheck(self):

        if not self.getcfg('sanityCheckPaths'):
            self.setcfg('sanityCheckPaths', {'files':["%s/lib/lib%s.a" % (x, x.lower()) for x in ["AMD", "BTF", "CAMD", "CCOLAMD", "CHOLMOD", "COLAMD",
                                                                                             "CXSparse", "KLU", "LDL", "RBio", "SPQR", "UMFPACK"]] +
                                                    ["CSparse3/lib/libcsparse.a"],
                                            'dirs':[ "MATLAB_Tools"]
                                           })

            self.log.info("Customized sanity check paths: %s" % self.getcfg('sanityCheckPaths'))

        Application.sanitycheck(self)
