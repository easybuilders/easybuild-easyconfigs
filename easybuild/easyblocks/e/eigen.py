##
# This file is an EasyBuild reciPY as per https://github.com/hpcugent/easybuild
#
# Copyright:: Copyright 2012-2016 Uni.Lu/LCSB, NTUA
# Authors::   Cedric Laczny <cedric.laczny@uni.lu>, Fotis Georgatos <fotis@cern.ch>, Kenneth Hoste
# License::   MIT/GPL
# $Id$
#
# This work implements a part of the HPCBIOS project and is a component of the policy:
# http://hpcbios.readthedocs.org/en/latest/HPCBIOS_2012-94.html
##
"""
EasyBuild support for building and installing Eigen, implemented as an easyblock

@author: Cedric Laczny (Uni.Lu)
@author: Fotis Georgatos (Uni.Lu)
@author: Kenneth Hoste (Ghent University)
"""

import os
import shutil
from distutils.version import LooseVersion

from easybuild.framework.easyblock import EasyBlock
from easybuild.tools.build_log import EasyBuildError
from easybuild.tools.filetools import mkdir


class EB_Eigen(EasyBlock):
    """
    Support for building Eigen.
    """

    def configure_step(self):
        """
        No configure for Eigen.
        """
        pass

    def build_step(self):
        """
        No build for Eigen.
        """
        pass

    def install_step(self):
        """
        Install by copying files to install dir
        """
        mkdir(os.path.join(self.installdir, 'include'), parents=True)
        for subdir in ['Eigen', 'unsupported']:
            srcdir = os.path.join(self.cfg['start_dir'], subdir)
            destdir = os.path.join(self.installdir, os.path.join('include', subdir))
            try:
                shutil.copytree(srcdir, destdir, ignore=shutil.ignore_patterns('CMakeLists.txt'))
            except OSError, err:
                raise EasyBuildError("Copying %s to installation dir %s failed: %s", srcdir, destdir, err)

        if LooseVersion(self.version) >= LooseVersion('3.0'):
            srcfile = os.path.join(self.cfg['start_dir'], 'signature_of_eigen3_matrix_library')
            destfile = os.path.join(self.installdir, 'include/signature_of_eigen3_matrix_library')
            try:
                shutil.copy2(srcfile, destfile)
            except OSError, err:
                raise EasyBuildError("Copying %s to installation dir %s failed: %s", srcfile, destfile, err)

    def sanity_check_step(self):
        """Custom sanity check for Eigen."""

        # both in Eigen 2.x an 3.x
        include_files = ['Array', 'Cholesky', 'Core', 'Dense', 'Eigen', 'Geometry', 'LU',
                         'LeastSquares', 'QR', 'QtAlignedMalloc', 'SVD', 'Sparse', 'StdVector']

        if LooseVersion(self.version) >= LooseVersion('3.0'):
            # only in 3.x
            include_files.extend(['CholmodSupport', 'Eigen2Support', 'Eigenvalues', 'Householder',
                                  'IterativeLinearSolvers', 'Jacobi', 'OrderingMethods', 'PaStiXSupport',
                                  'PardisoSupport', 'SparseCholesky', 'SparseCore', 'StdDeque', 'StdList',
                                  'SuperLUSupport', 'UmfPackSupport'])
        custom_paths = {
            'files': ['include/Eigen/%s' % x for x in include_files],
            'dirs': []
        }

        if LooseVersion(self.version) >= LooseVersion('3.0'):
            custom_paths['files'].append('include/signature_of_eigen3_matrix_library')

        super(EB_Eigen, self).sanity_check_step(custom_paths=custom_paths)

    def make_module_req_guess(self):
        """
        A dictionary of possible directories to look for.
        Include CPLUS_INCLUDE_PATH as an addition to default ones
        """
        guesses = super(EB_Eigen, self).make_module_req_guess()
        guesses.update({'CPLUS_INCLUDE_PATH': ['include']})
        return guesses
