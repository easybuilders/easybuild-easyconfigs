##
# Copyright 2005 Josiah Carlson 
# Copyright 2009 Stijn Deweirdt
# Copyright 2011 Pieter De Baets
# Copyright 2012 Kenneth Hoste

# original code from http://code.activestate.com/recipes/440554/
# Released under the PSF License:
#
# 1. This LICENSE AGREEMENT is between the Python Software Foundation
# ("PSF"), and the Individual or Organization ("Licensee") accessing and
# otherwise using this software ("Python") in source or binary form and
# its associated documentation.
#
# 2. Subject to the terms and conditions of this License Agreement, PSF
# hereby grants Licensee a nonexclusive, royalty-free, world-wide
# license to reproduce, analyze, test, perform and/or display publicly,
# prepare derivative works, distribute, and otherwise use Python
# alone or in any derivative version, provided, however, that PSF's
# License Agreement and PSF's notice of copyright, i.e., "Copyright (c)
# 2001, 2002, 2003, 2004, 2005, 2006 Python Software Foundation; All Rights
# Reserved" are retained in Python alone or in any derivative version
# prepared by Licensee.
#
# 3. In the event Licensee prepares a derivative work that is based on
# or incorporates Python or any part thereof, and wants to make
# the derivative work available to others as provided herein, then
# Licensee hereby agrees to include in any such work a brief summary of
# the changes made to Python.
#
# 4. PSF is making Python available to Licensee on an "AS IS"
# basis. PSF MAKES NO REPRESENTATIONS OR WARRANTIES, EXPRESS OR
# IMPLIED. BY WAY OF EXAMPLE, BUT NOT LIMITATION, PSF MAKES NO AND
# DISCLAIMS ANY REPRESENTATION OR WARRANTY OF MERCHANTABILITY OR FITNESS
# FOR ANY PARTICULAR PURPOSE OR THAT THE USE OF PYTHON WILL NOT
# INFRINGE ANY THIRD PARTY RIGHTS.
#
# 5. PSF SHALL NOT BE LIABLE TO LICENSEE OR ANY OTHER USERS OF PYTHON
# FOR ANY INCIDENTAL, SPECIAL, OR CONSEQUENTIAL DAMAGES OR LOSS AS
# A RESULT OF MODIFYING, DISTRIBUTING, OR OTHERWISE USING PYTHON,
# OR ANY DERIVATIVE THEREOF, EVEN IF ADVISED OF THE POSSIBILITY THEREOF.
#
# 6. This License Agreement will automatically terminate upon a material
# breach of its terms and conditions.
#
# 7. Nothing in this License Agreement shall be deemed to create any
# relationship of agency, partnership, or joint venture between PSF and
# Licensee. This License Agreement does not grant permission to use PSF
# trademarks or trade name in a trademark sense to endorse or promote
# products or services of Licensee, or any third party.
#
# 8. By copying, installing or otherwise using Python, Licensee
# agrees to be bound by the terms and conditions of this License
# Agreement.
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
import sys
import time

PIPE = subprocess.PIPE
STDOUT = subprocess.STDOUT

if subprocess.mswindows:
    from win32file import ReadFile, WriteFile #IGNORE:F0401 #@UnresolvedImport
    from win32pipe import PeekNamedPipe #IGNORE:F0401 #@UnresolvedImport
    import msvcrt #IGNORE:F0401
else:
    import select
    import fcntl

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

    if subprocess.mswindows:
        def send(self, inp):
            if not self.stdin:
                return None

            try:
                x = msvcrt.get_osfhandle(self.stdin.fileno()) #@UndefinedVariable
                (_, written) = WriteFile(x, inp)
            except ValueError:
                return self._close('stdin')
            except (subprocess.pywintypes.error, Exception), why:
                if why[0] in (109, errno.ESHUTDOWN):
                    return self._close('stdin')
                raise

            return written

        def _recv(self, which, maxsize):
            conn, maxsize = self.get_conn_maxsize(which, maxsize)
            if conn is None:
                return None

            try:
                x = msvcrt.get_osfhandle(conn.fileno()) #@UndefinedVariable
                (read, nAvail, _) = PeekNamedPipe(x, 0)
                if maxsize < nAvail:
                    nAvail = maxsize
                if nAvail > 0:
                    (_, read) = ReadFile(x, nAvail, None)
            except ValueError:
                return self._close(which)
            except (subprocess.pywintypes.error, Exception), why:
                if why[0] in (109, errno.ESHUTDOWN):
                    return self._close(which)
                raise

            if self.universal_newlines:
                read = self._translate_newlines(read)
            return read

    else:
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
                fcntl.fcntl(conn, fcntl.F_SETFL, flags| os.O_NONBLOCK)

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

def recv_some(p, t=.1, e=1, tr=5, stderr=0):
    if tr < 1:
        tr = 1
    x = time.time()+t
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
            time.sleep(max((x-time.time())/tr, 0))
    return ''.join(y)

def send_all(p, data):
    while len(data):
        sent = p.send(data)
        if sent is None:
            raise Exception(message)
        data = buffer(data, sent)

if __name__ == '__main__':
    if sys.platform == 'win32':
        shell, commands, tail = ('cmd', ('dir /w', 'echo HELLO WORLD'), '\r\n')
    else:
        shell, commands, tail = ('sh', ('ls', 'echo HELLO WORLD'), '\n')

    a = Popen(shell, stdin=PIPE, stdout=PIPE)
    print recv_some(a),
    for cmd in commands:
        send_all(a, cmd + tail)
        print recv_some(a),
    send_all(a, 'exit' + tail)
    print recv_some(a, e=0)
    a.wait()
