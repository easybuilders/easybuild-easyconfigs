.. image:: http://hpcugent.github.io/easybuild/images/easybuild_logo_small.png
   :align: center

`EasyBuild <https://hpcugent.github.io/easybuild>`_ is a software build
and installation framework that allows you to manage (scientific) software
on High Performance Computing (HPC) systems in an efficient way.

The **easybuild-easyconfigs** package provides a collection of well-tested
example *easyconfig files* for EasyBuild.
Easyconfig files are used to specify which software to build, which
version of the software (and its dependencies), which build parameters
to use (e.g., which compiler toolchain to use), etc.

The EasyBuild documentation is available at http://easybuild.readthedocs.org/.

The easybuild-easyconfigs package is hosted on GitHub, along
with an issue tracker for bug reports and feature requests, see
http://github.com/hpcugent/easybuild-easyconfigs.

Related Python packages:

* **easybuild-framework**

  * the EasyBuild framework, which includes the ``easybuild.framework`` and ``easybuild.tools`` Python
    packages that provide general support for building and installing software
  * GitHub repository: http://github.com/hpcugent/easybuild-framework
  * PyPi: https://pypi.python.org/pypi/easybuild-framework

* **easybuild-easyblocks**

  * a collection of easyblocks that implement support for building and installing (groups of) software packages
  * GitHub repository: http://github.com/hpcugent/easybuild-easyblocks
  * package on PyPi: https://pypi.python.org/pypi/easybuild-easyblocks

*Build status overview:*

* **master** branch:

  .. image:: https://travis-ci.org/hpcugent/easybuild-easyconfigs.svg?branch=master
      :target: https://travis-ci.org/hpcugent/easybuild-easyconfigs/branches

* **develop** branch:

  .. image:: https://travis-ci.org/hpcugent/easybuild-easyconfigs.svg?branch=develop
      :target: https://travis-ci.org/hpcugent/easybuild-easyconfigs/branches
