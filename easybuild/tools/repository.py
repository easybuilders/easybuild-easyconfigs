##
# Copyright 2009-2012 Stijn Deweirdt, Dries Verdegem, Kenneth Hoste, Pieter De Baets, Jens Timmerman
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
"""
Set of repository tools

We have a plain filesystem, an svn and a git repository
"""
import getpass
import os
import shutil
import socket
import sys
import tempfile
import time

import easybuild
from easybuild.tools.build_log import getLog, EasyBuildError
from easybuild.tools.config import repositoryPath, repositoryType
# try and load git (GitPython), OK if it fails if we don't use it
try:
    import git
    from git import GitCommandError
except ImportError:
    pass
# try and load pysvn, OK if it fails if we don't use it
try:
    import pysvn
    from pysvn import ClientError #IGNORE:E0611 pysvn fails to recognize ClientError is available
except ImportError:
    pass


log = getLog('repo')

class Repository:
    """
    Class representing an file system repository.
    """
    def __init__(self):
        log.debug("creating repository")
        self.repo = None
        self.wc = ""

        self.client = None

        self.setupRepo()
        self.createWorkingCopy()

    def __del__(self):
        self.cleanup()

    def setupRepo(self):
        """
        Set up file system repository.
        """
        log.debug("setting up repository")
        self.repo = self.wc = repositoryPath()

    def createWorkingCopy(self):
        """
        Create working copy.
        """
        os.chdir(self.repo)

    def addEasyconfig(self, cfg, name, version, stats, appendstats):
        """
        Add easyconfig to repository.
        Stats contains some build stats, this should be a list of dictionaries.
        appendstats is a boolean indicating if we should append to existing stats or not.
        """
        if not name.startswith(self.wc):
            name = os.path.join(self.wc, name)
        if not os.path.isdir(name):
            os.makedirs(name)

        ## destination
        dest = os.path.join(self.wc, name, "%s.eb" % (version))

        ## check if it's new/different from what's in svn
        #nope, always commit
        #if os.path.exists(dest) and self.checkIdent(cfg, dest):
        #    log.info("Dest file %s already exist but is identical to what is in the repository." % dest)
        #    return None

        try:
            ## copy file
            oldf = open(cfg)
            oldcontent = oldf.read()
            oldf.close()
            dest_file = open(dest, 'w')
            dest_file.write("# Built with %s on %s\n" % (easybuild.VERBOSE_VERSION, time.strftime("%Y-%m-%d_%H-%M-%S")))
            dest_file.write(oldcontent)
            if appendstats:
                statstemplate = "buildstats.append(%s)\n"
            else:
                statstemplate = "\n#Build statistics\nbuildstats=[%s]\n"

            dest_file.write(statstemplate % stats)
            dest_file.close()

        except IOError, err:
            log.exception("Copying file %s to %s (wc: %s) failed (%s)" % (cfg, dest, self.wc, err))
        return dest

    def commit(self, msg=None):
        """
        Commit working copy
        - add msg
        - add more info to msg
        """
        # does nothing by default
        pass

    def removeStartingComments(self, text):
        """
        removes the first lines from a given text,
        if the line starts with a '#'
        """
        lines = text.splitlines(True)
        i = 0
        for line in lines:
            if not line.startswith('#'):
                break
            else:
                i = i + 1
        return "\n".join(lines[i:])

    def checkIdent(self, src, dest):
        """
        Compare the content of 2 files.
        - return True is they are identical
        - assume wc is up-to-date (local == remote)
        """
        srctxt = file(src).read()
        local = file(dest).read()

        srctxt = self.removeStartingComments(srctxt)
        local = self.removeStartingComments(local)

        if local == srctxt:
            log.debug("Identical content found for %s (%s) and %s (%s)" % (src, srctxt, dest, local))
            return True
        else:
            log.debug("Different content found for %s (%s) and %s (%s)" % (src, srctxt, dest, local))
            return False

    def cleanup(self):
        """
        Clean up working copy.
        """
        return


class GitRepository(Repository):
    """
    Class representing a git repository.
    """

    def __init__(self):
        self.path = None
        Repository.__init__(self)


        # check whether git module was loaded (globally)
        if not 'git' in sys.modules or not ('git' in locals() and locals()['git'] == sys.modules['git']):
            log.exception("Failed to load GitPython. Make sure it is installed "
                          "properly. Run 'python -c \"import git\"' to test.")

    def setupRepo(self):
        """
        Set up git repository.
        """
        Repository.setupRepo(self)
        log.debug("setting up git repository")
        self.repo = self.wc[0]
        self.path = self.wc[1]
        self.wc = self.repo
        log.debug("repository %s configured with path %s" % (self.repo, self.path))

    def createWorkingCopy(self):
        """
        Create git working copy.
        """
        # GitPython version 0.1.x (identified as 'git') has no init method, but uses create instead
        # TODO make a config option to add a directory to a local wc somewhere, so we don't need to
        # create a local wc every time.
        self.wc = tempfile.mkdtemp(prefix='git-wc-')

        ## try to get a copy of
        try:
            client = git.Git(self.wc)
            out = client.clone(self.repo)
            # out  = 'Cloning into easybuild...'
            reponame = out.split()[-1].strip(".").strip("'")
            log.debug("rep name is %s" % reponame)
        except GitCommandError, err:
            # it might already have existed
            log.warning("Git local repo initialization failed, it might already exist: %s" % err)

        # local repo should now exist, let's connect to it again
        try:
            self.wc = os.path.join(self.wc, reponame)
            log.debug("connectiong to git repo in %s" % self.wc)
            self.client = git.Git(self.wc)
        except GitCommandError, err:
            log.error("Could not create a local git repo in wc %s: %s" % (self.wc, err))

        # try to get the remote data in the local repo
        try:
            res = self.client.pull()
            log.debug("pulled succesfully to %s in %s" % (res, self.wc))
        except GitCommandError, err:
            log.exception("pull in working copy %s went wrong: %s" % (self.wc, err))

    def addEasyconfig(self, cfg, name, version, stats, append):
        """
        Add easyconfig to git repository.
        """
        log.debug("Adding cfg: %s with name %s" % (cfg, name))
        log.debug("Adding cfg: in %s on path %s" % (self.wc, self.path))
        if  name.startswith(self.wc):
            name = name.replace(self.wc, "", 1) #remove self.wc again
        name = os.path.join(self.wc, self.path, name) #create proper name, with path inside repo in it
        dest = Repository.addEasyconfig(self, cfg, name, version, stats, append)
        ## add it to version control
        if dest:
            try:
                #log.debug("Going to add %s (wc: %s, cwd %s)"%(dest, self.wc, os.getcwd()))
                self.client.add(dest)
            except GitCommandError, err:
                log.warning("adding %s to git failed: %s" % (dest, err))

    def commit(self, msg=None):
        """
        Commit working copy to git repository
        """
        log.debug("committing in git: %s" % msg)
        completemsg = "EasyBuild-commit from %s (time: %s, user: %s) \n%s" % (socket.gethostname(), time.strftime("%Y-%m-%d_%H-%M-%S"), getpass.getuser(), msg)
        log.debug("git status: %s" % self.client.status())
        try:
            self.client.commit('-am "%s"' % completemsg)
            log.debug("succesfull commit")
        except GitCommandError, err:
            log.warning("Commit from working copy %s (msg: %s) failed, empty commit?\n%s" % (self.wc, msg, err))
        try:
            info = self.client.push()
            log.debug("push info: %s " % info)
        except GitCommandError, err:
            log.warning("Push from working copy %s to remote %s (msg: %s) failed: %s" % (self.wc, self.repo, msg, err))

    def cleanup(self):
        """
        Clean up git working copy.
        """
        try:
            shutil.rmtree(self.wc)
        except IOError, err:
            log.exception("Can't remove working copy %s: %s" % (self.wc, err))


class SvnRepository(Repository):
    """
    class representing an svn repository
    """
    def __init__(self):
        Repository.__init__(self)

        if not 'pysvn' in sys.modules or not locals()['pysvn'] == sys.modules['pysvn']:
            log.exception("Failed to load pysvn. Make sure it is installed "
                          "properly. Run 'python -c \"import pysvn\"' to test.")

    def setupRepo(self):
        """
        Set up SVN repository.
        """
        Repository.setupRepo(self)

        ## try to connect to the repository
        log.debug("Try to connect to repository %s" % self.repo)
        try:
            self.client = pysvn.Client()
            self.client.exception_style = 0
        except ClientError:
            log.exception("Svn Client initialization failed.")

        try:
            if not self.client.is_url(self.repo):
                log.error("Provided repository %s is not a valid svn url" % self.repo)
        except ClientError:
            log.exception("Can't connect to svn repository %s" % self.repo)

    def createWorkingCopy(self):
        """
        Create SVN working copy.
        """
        self.wc = tempfile.mkdtemp(prefix='svn-wc-')

        # Update wc (or part of it)
        try:
            os.chdir(self.wc)
        except OSError, err:
            log.exception("Couldn't chdir to wc %s: %s" % (self.wc, err))

        ## check if tmppath exists
        ## this will trigger an error if it does not exist
        try:
            self.client.info2(self.repo, recurse=False)
        except ClientError:
            log.exception("Getting info from %s failed." % self.wc)

        try:
            res = self.client.update(self.wc)
            log.debug("Updated to revision %s in %s" % (res, self.wc))
        except ClientError:
            log.exception("Update in wc %s went wrong" % self.wc)

        if len(res) == 0:
            log.error("Update returned empy list (working copy: %s)" % (self.wc))

        if res[0].number == -1:
            ## revision number of update is -1
            ## means nothing has been checked out
            try:
                res = self.client.checkout(self.repo, self.wc)
                log.debug("Checked out revision %s in %s" % (res.number, self.wc))
            except ClientError, err:
                log.exception("Checkout of path / in working copy %s went wrong: %s" % (self.wc, err))

    def addEasyconfig(self, cfg, name, version, stats, append):
        """
        Add easyconfig to SVN repository.
        """
        if not os.path.isdir(name):
            self.client.mkdir(name, "Creating path %s" % name)
        dest = Repository.addEasyconfig(self, cfg, name, version, stats, append)
        log.debug("destination = %s" % dest)
        if dest:
            log.debug("destination status: %s" % self.client.status(dest))

            if self.client and not self.client.status(dest)[0].is_versioned:
                ## add it to version control
                log.debug("Going to add %s (working copy: %s, cwd %s)" % (dest, self.wc, os.getcwd()))
                self.client.add(dest)

    def commit(self, msg=None):
        """
        Commit working copy to SVN repository
        """
        completemsg = "EasyBuild-commit from %s (time: %s, user: %s) \n%s" % (socket.gethostname(), time.strftime("%Y-%m-%d_%H-%M-%S"), getpass.getuser(), msg)
        try:
            self.client.checkin(self.wc, completemsg, recurse=True)
        except ClientError, err:
            log.exception("Commit from working copy %s (msg: %s) failed: %s" % (self.wc, msg, err))

    def cleanup(self):
        """
        Clean up SVN working copy.
        """
        try:
            shutil.rmtree(self.wc)
        except OSError, err:
            log.exception("Can't remove working copy %s: %s" % (self.wc, err))


def getRepository():
    """
    Factory method, returning a repository depending on the configuration file
    """
    typ = repositoryType()
    if typ == 'fs':
        return Repository()
    elif typ == 'git':
        return GitRepository()
    elif typ == 'svn':
        return SvnRepository()
    else:
        log.error("invalid repositoryType detected, check config file")
        return None


if __name__ == "__main__":
    try:
        s = getRepository()
    except EasyBuildError, e:
        print "Initialization failed: %s" % e
