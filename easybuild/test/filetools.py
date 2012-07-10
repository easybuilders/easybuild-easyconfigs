import os
import re

from unittest import TestCase, TestSuite

import easybuild.tools.filetools as ft

class FileToolsTest(TestCase):

    def runTest(self):
        cmd = ft.extractCmd("test.zip")
        self.assertEqual("unzip -qq test.zip", cmd)

        cmd = ft.extractCmd("/tmp/test.tar")
        self.assertEqual("tar xf /tmp/test.tar", cmd)

        cmd = ft.extractCmd("/tmp/test.tar.gz")
        self.assertEqual("tar xzf /tmp/test.tar.gz", cmd)

        cmd = ft.extractCmd("/tmp/test.tgz")
        self.assertEqual("tar xzf /tmp/test.tgz", cmd)

        cmd = ft.extractCmd("/tmp/test.bz2")
        self.assertEqual("bunzip2 /tmp/test.bz2", cmd)

        cmd = ft.extractCmd("/tmp/test.tbz")
        self.assertEqual("tar xfj /tmp/test.tbz", cmd)
        cmd = ft.extractCmd("/tmp/test.tar.bz2")
        self.assertEqual("tar xfj /tmp/test.tar.bz2", cmd)

def suite():
    return TestSuite([FileToolsTest()])
