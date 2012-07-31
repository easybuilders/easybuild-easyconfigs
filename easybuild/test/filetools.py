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
        self.assertEqual("tar xjf /tmp/test.tbz", cmd)
        cmd = ft.extractCmd("/tmp/test.tar.bz2")
        self.assertEqual("tar xjf /tmp/test.tar.bz2", cmd)


        (out, ec) = ft.run_cmd("echo hello")
        self.assertEqual(out, "hello\n")
        # no reason echo hello could fail
        self.assertEqual(ec, 0)

        (out, ec) = ft.run_cmd_qa("echo question", {"question":"answer"})
        self.assertEqual(out, "question\n")
        # no reason echo hello could fail
        self.assertEqual(ec, 0)

        self.assertEqual(True, ft.run_cmd("echo hello", simple=True))
        self.assertEqual(False, ft.run_cmd("exit 1", simple=True, log_all=False,log_ok=False))

        name = ft.convertName("test+test-test")
        self.assertEqual(name, "testplustestmintest")
        name = ft.convertName("test+test-test", True)
        self.assertEqual(name, "TESTPLUSTESTMINTEST")


        errors = ft.parselogForError("error failed", True)
        self.assertEqual(len(errors), 1)

        # I expect tests to be run from the base easybuild directory
        self.assertEqual(os.getcwd(), ft.findBaseDir())

def suite():
    return TestSuite([FileToolsTest()])
