# toolkit should be first to allow hacks to work
import easybuild.test.toolkit as t
import easybuild.test.asyncprocess as a
import easybuild.test.easyblock as e
import easybuild.test.modulegenerator as mg
import easybuild.test.modules as m

import unittest

suite = unittest.TestSuite(map(lambda x: x.suite(), [t,e,mg,m,a]))
unittest.TextTestRunner().run(suite)
