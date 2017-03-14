##
# Copyright 2017 Free University of Brussels (VUB)
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
EasyBuild support for MXNet, implemented as an easyblock

@author: Ward Poelmans (Free University of Brussels)
"""
import os
import shutil
from distutils.version import LooseVersion

from easybuild.easyblocks.generic.makecp import MakeCp
from easybuild.easyblocks.generic.pythonpackage import PythonPackage
from easybuild.easyblocks.generic.rpackage import RPackage
from easybuild.framework.easyconfig import CUSTOM
from easybuild.tools.build_log import EasyBuildError
from easybuild.tools.filetools import apply_regex_substitutions, copy_file, symlink, write_file, mkdir
from easybuild.tools.modules import get_software_root, get_software_version
from easybuild.tools.systemtools import get_shared_lib_ext


class EB_MXNet(MakeCp):
    """Easyblock to build and install MXNet"""

    @staticmethod
    def extra_options():
        """Change default values of options"""
        extra = MakeCp.extra_options()
        # files_to_copy is not mandatory here
        extra['files_to_copy'][2] = CUSTOM
        return extra

    def __init__(self, *args, **kwargs):
        """Initialize custom class variables."""
        super(EB_MXNet, self).__init__(*args, **kwargs)

        self.mxnet_src_dir = None
        self.py_ext = None
        self.r_ext = None

    def extract_step(self):
        """
        Prepare a combined MXNet source tree. Move all submodules
        to their right place.
        """
        # Extract everything into separate directories.
        super(EB_MXNet, self).extract_step()

        # Find the full path to the directory that was unpacked from mxnet-*.tar.gz.
        for srcdir in os.listdir(self.builddir):
            if srcdir.startswith("mxnet-"):
                self.mxnet_src_dir = os.path.join(self.builddir, srcdir)
                break

        if self.mxnet_src_dir is None:
            raise EasyBuildError("Could not find the MXNet source directory")

        self.log.debug("MXNet dir is: %s", self.mxnet_src_dir)

        for srcdir in os.listdir(self.builddir):
            if srcdir.startswith("mxnet-"):
                continue
            else:
                submodule, _, _ = srcdir.rpartition('-')
                try:
                    newdir = os.path.join(self.mxnet_src_dir, submodule)
                    olddir = os.path.join(self.builddir, srcdir)
                    # first remove empty existing directory
                    os.rmdir(newdir)
                    shutil.move(olddir, newdir)
                except IOError, err:
                    raise EasyBuildError("Failed to move %s to %s: %s", olddir, newdir, err)

        # the nnvm submodules has dmlc-core as a submodule too. Let's up a symlink in place.
        try:
            newdir = os.path.join(self.mxnet_src_dir, "nnvm", "dmlc-core")
            olddir = os.path.join(self.mxnet_src_dir, "dmlc-core")
            os.rmdir(newdir)
            symlink(olddir, newdir)
        except IOError, err:
            raise EasyBuildError("Failed to symlink %s to %s: %s", olddir, newdir, err)

    def configure_step(self):
        """Patch 'config.mk' file to use EB stuff"""
        copy_file('make/config.mk', '.')

        regex_subs = [
            (r"export CC = gcc", r"# \g<0>"),
            (r"export CXX = g\+\+", r"# \g<0>"),
            (r"(?P<var>ADD_LDFLAGS\s*=)\s*$", r"\g<var> %s" % os.environ['EBVARCFLAGS']),
            (r"(?P<var>ADD_CFLAGS\s*=)\s*$", r"\g<var> %s" % os.environ['EBVARLDFLAGS']),
        ]

        toolchain_blas = self.toolchain.definition().get('BLAS', None)[0]
        if toolchain_blas == 'imkl':
            blas = "mkl"
            imkl_version = get_software_version('imkl')
            if LooseVersion(imkl_version) >= LooseVersion('17'):
                regex_subs.append(("USE_MKL2017 = 0", "USE_MKL2017 = 1"))
            regex_subs.append((r"(?P<var>MKLML_ROOT=).*$", r"# \g<var>%s" % os.environ["MKLROOT"]))
        elif toolchain_blas in ['ACML', 'ATLAS']:
            blas = "atlas"
        elif toolchain_blas == 'OpenBLAS':
            blas = "openblas"
        elif toolchain_blas is None:
            # This toolchain has no BLAS library
            raise EasyBuildError("No BLAS library found in the toolchain")

        regex_subs.append((r'USE_BLAS =.*', 'USE_BLAS = %s' % blas))

        if get_software_root('NNPACK'):
            regex_subs.append(("USE_NNPACK = 0", "USE_NNPACK = 1"))

        apply_regex_substitutions('config.mk', regex_subs)

        super(EB_MXNet, self).configure_step()

    def install_step(self):
        """Specify list of files to copy"""
        self.cfg['files_to_copy'] = ['bin', 'include', 'lib',
                                     (['dmlc-core/include/dmlc', 'nnvm/include/nnvm'], 'include')]
        super(EB_MXNet, self).install_step()

    def extensions_step(self):
        """Build & Install both Python and R extension"""
        # we start with the python bindings
        self.py_ext = PythonPackage(self, {'name': 'mxnet'})
        self.py_ext.module_generator = self.module_generator
        self.py_ext.src = os.path.join(self.mxnet_src_dir, "python")
        os.chdir(self.py_ext.src)

        self.py_ext.prerun()
        self.py_ext.run(unpack_src=False)
        self.py_ext.postrun()

        # next up, the R bindings
        self.r_ext = RPackage(self, {'name': 'R-package'})
        self.r_ext.module_generator = self.module_generator
        self.r_ext.src = os.path.join(self.mxnet_src_dir, "R-package")
        try:
            os.chdir(self.r_ext.src)
            mkdir("inst")
            symlink(os.path.join(self.installdir, "lib"), "inst/libs")
            symlink(os.path.join(self.installdir, "include"), "inst/include")
        except IOError, err:
            raise EasyBuildError("Failed to prepare the 'inst' directory for the R bindings: %s", err)

        namespace = ["import(Rcpp)", "import(methods)", ""]
        write_file("NAMESPACE", "\n".join(namespace))
        self.r_ext.prerun()
        self.r_ext.run()
        self.r_ext.postrun()

    def sanity_check_step(self):
        """Check for main library files for MXNet"""
        custom_paths = {
            'files': ["lib/libmxnet.%s" % ext for ext in ['a', get_shared_lib_ext()]],
            'dirs': [],
        }
        super(EB_MXNet, self).sanity_check_step(custom_paths=custom_paths)
        self.py_ext.sanity_check_step()
        self.r_ext.sanity_check_step()

    def make_module_extra(self, *args, **kwargs):
        """Custom variables for MXNet module."""
        txt = super(EB_MXNet, self).make_module_extra(*args, **kwargs)
        txt += self.py_ext.make_module_extra(*args, **kwargs)
        txt += self.r_ext.make_module_extra(*args, **kwargs)
        return txt
