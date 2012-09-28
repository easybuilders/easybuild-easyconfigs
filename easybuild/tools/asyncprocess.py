##
# Copyright 2005 Josiah Carlson
# The Asynchronous Python Subprocess recipe was originally created by Josiah Carlson.
# and released under the GPL v2 on March 14, 2012
#
# http://code.activestate.com/recipes/440554/
#
# Copyright 2009-2012 Stijn De Weirdt
# Copyright 2010 Dries Verdegem
# Copyright 2010-2012 Kenneth Hoste
# Copyright 2011 Pieter De Baets
# Copyright 2011-2012 Jens Timmerman
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

"""Module to allow Asynchronous subprocess use on Windows and Posix platforms

The 'subprocess' module in Python 2.4 has made creating and accessing subprocess
streams in Python relatively convenient for all supported platforms,
but what if you want to interact with the started subprocess?
That is, what if you want to send a command, read the response,
and send a new command based on that response?

Now there is a solution.
The included subprocess.Popen subclass adds three new commonly used methods:
 recv(maxsize=None)
 recv_err(maxsize=None)
 and send(input)

along with a utility method:
 send_recv(input='', maxsize=None).

recv() and recv_err() both read at most maxsize bytes from the started subprocess.
send() sends strings to the started subprocess. send_recv() will send the provided input,
and read up to maxsize bytes from both stdout and stderr.

If any of the pipes are closed, the attributes for those pipes will be set to None,
and the methods will return None.

- downloaded 05/08/2010
- modified
-- added STDOUT handle
"""

import errno
import os
import subprocess
import time

PIPE = subprocess.PIPE
STDOUT = subprocess.STDOUT

import select  #@UnresolvedImport
import fcntl  #@UnresolvedImport


class Popen(subprocess.Popen):
    def recv(self, maxsize=None):
        return self._recv('stdout', maxsize)

    def recv_err(self, maxsize=None):
        return self._recv('stderr', maxsize)

    def send_recv(self, inp='', maxsize=None):
        return self.send(inp), self.recv(maxsize), self.recv_err(maxsize)

    def get_conn_maxsize(self, which, maxsize):
        if maxsize is None:
            maxsize = 1024
        elif maxsize < 1:
            maxsize = 1
        return getattr(self, which), maxsize

    def _close(self, which):
        getattr(self, which).close()
        setattr(self, which, None)

    def send(self, inp):
        if not self.stdin:
            return None

        if not select.select([], [self.stdin], [], 0)[1]:
            return 0

        try:
            written = os.write(self.stdin.fileno(), inp)
        except OSError, why:
            if why[0] == errno.EPIPE: #broken pipe
                return self._close('stdin')
            raise

        return written

    def _recv(self, which, maxsize):
        conn, maxsize = self.get_conn_maxsize(which, maxsize)
        if conn is None:
            return None

        flags = fcntl.fcntl(conn, fcntl.F_GETFL)
        if not conn.closed:
            fcntl.fcntl(conn, fcntl.F_SETFL, flags | os.O_NONBLOCK)

        try:
            if not select.select([conn], [], [], 0)[0]:
                return ''

            r = conn.read(maxsize)
            if not r:
                return self._close(which)

            if self.universal_newlines:
                r = self._translate_newlines(r)
            return r
        finally:
            if not conn.closed:
                fcntl.fcntl(conn, fcntl.F_SETFL, flags)

message = "Other end disconnected!"

def recv_some(p, t=.2, e=1, tr=5, stderr=0):
    if tr < 1:
        tr = 1
    x = time.time() + t
    y = []
    r = ''
    pr = p.recv
    if stderr:
        pr = p.recv_err
    while time.time() < x or r:
        r = pr()
        if r is None:
            if e:
                raise Exception(message)
            else:
                break
        elif r:
            y.append(r)
        else:
            time.sleep(max((x - time.time()) / tr, 0))
    return ''.join(y)

def send_all(p, data):
    while len(data):
        sent = p.send(data)
        if sent is None:
            raise Exception(message)
        data = buffer(data, sent)


