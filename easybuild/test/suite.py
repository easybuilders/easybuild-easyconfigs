##
# Copyright 2012 Toon Willems
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
""" this module is a collection of all the testcases """
import unittest

# toolkit should be first to allow hacks to work
import easybuild.test.toolkit as t
import easybuild.test.asyncprocess as a
import easybuild.test.easyblock as e
import easybuild.test.modulegenerator as mg
import easybuild.test.modules as m
import easybuild.test.filetools as f
import easybuild.test.repository as r
import easybuild.test.robot as robot

# call suite() for each module and then run them all
suite = unittest.TestSuite(map(lambda x: x.suite(), [t, r, e, mg, m, f, a, robot]))
unittest.TextTestRunner().run(suite)
