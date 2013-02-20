##
# This file is an EasyBuild reciPY as per https://github.com/hpcugent/easybuild
#
# Copyright:: Copyright 2012-2013 University of Luxembourg/Luxembourg Centre for Systems Biomedicine
# Authors::   Cedric Laczny <cedric.laczny@uni.lu>, Fotis Georgatos <fotis.georgatos@uni.lu>, Kenneth Hoste
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

from easybuild.framework.easyblock import EasyBlock


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
        srcdir = os.path.join(self.cfg['start_dir'], 'Eigen')
        destdir = os.path.join(self.installdir, 'include/Eigen')
        try:
                os.makedirs(os.path.dirname(destdir))
                shutil.copytree(srcdir, destdir)
        except OSError, err:
            self.log.error("Copying %s to installation dir %s failed: %s" % (srcdir, destdir, err))

    def sanity_check_step(self):
        """Custom sanity check for Eigen."""

        custom_paths = {
                        'files': ['include/Eigen/%s' % x for x in ['Array', 'Cholesky', 'CholmodSupport',
                                                                   'Core', 'Dense', 'Eigen', 'Eigen2Support',
                                                                   'Eigenvalues', 'Geometry', 'Householder',
                                                                   'IterativeLinearSolvers', 'Jacobi', 'LU',
                                                                   'LeastSquares', 'OrderingMethods',
                                                                   'PaStiXSupport', 'PardisoSupport', 'QR',
                                                                   'QtAlignedMalloc', 'SVD', 'Sparse',
                                                                   'SparseCholesky', 'SparseCore', 'StdDeque',
                                                                   'StdList', 'StdVector', 'SuperLUSupport',
                                                                   'UmfPackSupport']],
                        'dirs': []
                       }
        super(EB_Eigen, self).sanity_check_step(custom_paths=custom_paths)

    def make_module_req_guess(self):
        """  
        A dictionary of possible directories to look for.
        Include CPLUS_INCLUDE_PATH as an addition to default ones
        """
        guesses = super(EB_Eigen, self).make_module_req_guess()
        guesses.update({'CPLUS_INCLUDE_PATH': ['include']})
        return guesses
