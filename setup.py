import glob
import os
import shutil
import sys
from distutils import log

VERSION = "0.9.0dev"
API_VERSION = VERSION.split('.')[0]
EB_VERSION = '.'.join(VERSION.split('.')[0:2])
if VERSION.endswith('dev'):
    EB_VERSION += 'dev'

# log levels: 0 = WARN (default), 1 = INFO, 2 = DEBUG
log.set_verbosity(1)

# try setuptools, fall back to distutils if needed
try:
    from setuptools import setup
    log.info("Installing with setuptools.setup...")
    install_package = 'setuptools'

except ImportError, err:
    log.info("Failed to import setuptools.setup (%s), so falling back to distutils.setup" % err)
    from distutils.core import setup
    install_package = 'distutils'

# utility function to read README file
def read(fname):
    """Read contents of given file."""
    return open(os.path.join(os.path.dirname(__file__), fname)).read()

# utility function to get list of data files (i.e. easyconfigs)
def get_data_files():
    """
    Return list of data files, i.e. easyconfigs, patches, etc.,
    and retain directory structure.
    """
    data_files = []
    for dirname,dirs,files in os.walk(os.path.join('easybuild', 'easyconfigs')):
        if files:
            data_files.append((dirname, [os.path.join(dirname, f) for f in files]))
    return data_files

log.info("Installing version %s (required versions: API >= %s, easyblocks >= %s)" % (VERSION, API_VERSION, EB_VERSION))

setup(
    name = "easybuild-easyconfigs",
    version = VERSION,
    author = "EasyBuild community",
    author_email = "easybuild@lists.ugent.be",
    description = """EasyBuild is a software installation framework in Python that allows you to \
install software in a structured and robust way.
This package contains a collection of easyconfigs, i.e. simple text files written in Python syntax \
that specify the build parameters for software packages (version, compiler toolchain, dependency \
versions, etc.)""",
    license = "GPLv2",
    keywords = "software build building installation installing compilation HPC scientific",
    url = "http://hpcugent.github.com/easybuild",
    data_files = get_data_files(),
    long_description = read("README.md"),
    classifiers = [
                   "Development Status :: 5 - Production/Stable",
                   "Environment :: Console",
                   "Intended Audience :: System Administrators",
                   "License :: OSI Approved :: GNU General Public License v2 (GPLv2)",
                   "Operating System :: POSIX :: Linux",
                   "Programming Language :: Python :: 2.4",
                   "Topic :: Software Development :: Build Tools",
                  ],
    platforms = "Linux",
    # install_requires list is not enforced, because of 'old-and-unmanageable' setup?
    # do we even want the dependency, since it's artificial?
    install_requires = [
                        "easybuild-framework >= %s.0" % API_VERSION,
                        "easybuild-easyblocks >= %s" % EB_VERSION
                       ],
    zip_safe = False
)

