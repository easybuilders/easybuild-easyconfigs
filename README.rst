.. image:: https://easybuilders.github.io/easybuild/images/easybuild_logo_small.png
   :align: center

`EasyBuild <https://easybuilders.github.io/easybuild>`_ is a software build
and installation framework that allows you to manage (scientific) software
on High Performance Computing (HPC) systems in an efficient way.

<<<<<<< HEAD
The **easybuild-easyblocks** package provides a collection of *easyblocks* for
EasyBuild. Easyblocks are Python modules that implement the install procedure for a
(group of) software package(s). Together with the EasyBuild framework,
they allow to easily build and install supported software packages.

The EasyBuild documentation is available at http://easybuild.readthedocs.org/.

The easybuild-easyblocks source code is hosted on GitHub, along
with an issue tracker for bug reports and feature requests, see
https://github.com/easybuilders/easybuild-easyblocks.
=======
The **easybuild-easyconfigs** package provides a collection of well-tested
example *easyconfig files* for EasyBuild.
Easyconfig files are used to specify which software to build, which
version of the software (and its dependencies), which build parameters
to use (e.g., which compiler toolchain to use), etc.

The EasyBuild documentation is available at http://easybuild.readthedocs.org/.

The easybuild-easyconfigs package is hosted on GitHub, along
with an issue tracker for bug reports and feature requests, see
https://github.com/easybuilders/easybuild-easyconfigs.
>>>>>>> 22ab263e7049b39a53a588652d8579107c1255f3

Related Python packages:

* **easybuild-framework**

  * the EasyBuild framework, which includes the ``easybuild.framework`` and ``easybuild.tools`` Python
    packages that provide general support for building and installing software
  * GitHub repository: https://github.com/easybuilders/easybuild-framework
  * PyPi: https://pypi.python.org/pypi/easybuild-framework

<<<<<<< HEAD
* **easybuild-easyconfigs**

  * a collection of example easyconfig files that specify which software to build,
    and using which build options; these easyconfigs will be well tested
    with the latest compatible versions of the easybuild-framework and easybuild-easyblocks packages
  * GitHub repository: https://github.com/easybuilders/easybuild-easyconfigs
  * PyPi: https://pypi.python.org/pypi/easybuild-easyconfigs
=======
* **easybuild-easyblocks**

  * a collection of easyblocks that implement support for building and installing (groups of) software packages
  * GitHub repository: https://github.com/easybuilders/easybuild-easyblocks
  * package on PyPi: https://pypi.python.org/pypi/easybuild-easyblocks
>>>>>>> 22ab263e7049b39a53a588652d8579107c1255f3

*Build status overview:*

* **master** branch:

<<<<<<< HEAD
  .. image:: https://travis-ci.org/easybuilders/easybuild-easyblocks.svg?branch=master
      :target: https://travis-ci.org/easybuilders/easybuild-easyblocks/branches

* **develop** branch:

  .. image:: https://travis-ci.org/easybuilders/easybuild-easyblocks.svg?branch=develop
      :target: https://travis-ci.org/easybuilders/easybuild-easyblocks/branches
=======
  .. image:: https://travis-ci.org/easybuilders/easybuild-easyconfigs.svg?branch=master
      :target: https://travis-ci.org/easybuilders/easybuild-easyconfigs/branches

* **develop** branch:

  .. image:: https://travis-ci.org/easybuilders/easybuild-easyconfigs.svg?branch=develop
      :target: https://travis-ci.org/easybuilders/easybuild-easyconfigs/branches
>>>>>>> 22ab263e7049b39a53a588652d8579107c1255f3
