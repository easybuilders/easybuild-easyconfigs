import os
import re

from unittest import TestCase, TestSuite
from easybuild.tools.asyncprocess import Popen
import easybuild.tools.asyncprocess as p

class AsyncProcessTest(TestCase):

    def setUp(self):
        self.shell = Popen('sh', stdin=p.PIPE, stdout=p.PIPE, shell=True, executable='/bin/bash')

    def runTest(self):
        p.send_all(self.shell, "echo hello\n")
        self.assertEqual(p.recv_some(self.shell), "hello\n")

        p.send_all(self.shell, "echo hello world\n")
        self.assertEqual(p.recv_some(self.shell), "hello world\n")

        p.send_all(self.shell, "exit\n")
        self.assertEqual("", p.recv_some(self.shell, e=0))
        self.assertRaises(Exception, p.recv_some, self.shell)

def suite():
    return TestSuite([AsyncProcessTest()])

