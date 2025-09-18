# Check that file was sourced, not executed
(return 0 2>/dev/null) && sourced=1 || sourced=0

if [ "$sourced" == 0 ]; then
    echo "File was not sourced, use:"
    echo "source setup_easybuild_environment.sh"
    exit 1
fi

# some non-default settings
export EASYBUILD_PREFIX=/readonly/dodrio/scratch/projects/2022_200/software/apps/${VSC_OS_LOCAL}/${VSC_ARCH_LOCAL}${VSC_ARCH_SUFFIX}
export EASYBUILD_UMASK=002 # Make sure the group has full access
export EASYBUILD_RPATH=True # Enable use of RPATH for linking with libraries. This is actually the default, but make it explicit in combination with EASYBUILD_FILTER_ENV_VARS=LD_LIBRARY_PATH
export EASYBUILD_FILTER_ENV_VARS=LD_LIBRARY_PATH # Since libraries are linked with RPATH, we do not need to use LD_LIBRARY_PATH
export EASYBUILD_DETECT_LOADED_MODULES=error # Detect loaded EasyBuild-generated modules, act accordingly
export EASYBUILD_MINIMAL_TOOLCHAINS=True # Use minimal toolchain when resolving dependencies
export EASYBUILD_USE_EXISTING_MODULES=True # Use existing modules when resolving dependencies with minimal toolchains

builddir=/dodrio/scratch/projects/2022_200/easybuild/tmp/$USER
mkdir -p ${builddir}
export EASYBUILD_BUILDPATH=${builddir}
export TMPDIR=${builddir}


# Make sure no modules are loaded
module purge

# Make sure existing modules are taken into account
module use ${EASYBUILD_PREFIX}/modules/all
module load EasyBuild

dodrio-bind-readonly /bin/bash
