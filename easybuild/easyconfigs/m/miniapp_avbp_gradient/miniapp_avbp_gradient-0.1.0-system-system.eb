easyblock = 'CMakeMake'

name = 'miniapp_avbp_gradient'
version = '0.1.0'

homepage = 'https://gitlab.com/cerfacs/open-source/miniapp_avbp_gradient'
description = """miniapp_avbp_gradient"""

# toolchain: load nvhpc module
toolchain = {'name': 'system', 'version': 'system'}
allow_empty_toolchain = True

# local source tarball 
# #source_urls = ['file:path_to/easybuild_folder/easyconfigs/sources/']
sources = [{
    'filename': 'miniapp_avbp_gradient.tar.gz',
    'extract_cmd': 'tar xzf %s',  # extract the tarball
}]

# Tell EasyBuild the directory name after extraction
start_dir = 'versions/version_de_base'

# CMake configuration options (passed to cmake)
# Note: we explicitly set the Fortran compiler to mpif90 (your CMakeLists also sets this)
configopts = (
    "-DCMAKE_BUILD_TYPE=Release "
    "-DCMAKE_Fortran_COMPILER=${FC} "
    "-DCMAKE_C_COMPILER=${CC} "
    "-DCMAKE_CXX_COMPILER=${CXX} "
    "-DCMAKE_Fortran_MODULE_DIRECTORY=%(builddir)s/mod "
)


builddependencies = []

installopts = ''

buildopts = '-j 8'

# Skip the install step since there's no install target
skipsteps = ['install']

# Manually install files after build
postinstallcmds = [
    'mkdir -p %(installdir)s/bin',
    'cp %(builddir)s/easybuild_obj/test %(installdir)s/bin/',
]

sanity_check_paths = {
    'files': ['bin/test'],  # Check that the 'test' executable exists
    'dirs': ['bin'],        # Check that the 'bin' directory exists
}


