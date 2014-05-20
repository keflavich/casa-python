from __future__ import print_function

import os
import errno
import stat
import tempfile
import subprocess
import platform
import sys
import optparse

if sys.version_info[0] == 2 and sys.version_info[1] < 6:
    raise Exception("Cannot run this script with python versions lower than 2.6."
                    "  Try to find a more recent python installation.")

from distutils.spawn import find_executable
from hashlib import md5
from urllib import urlopen

USER_DIR = os.path.join(os.path.expanduser('~'), '.casa')
BIN_DIR = os.path.join(os.path.expanduser('~'), '.casa', 'bin')
USER_SITE = os.path.join(os.path.expanduser('~'), '.casa', 'lib', 'python{pv}', 'site-packages')

PIP_URL = "https://pypi.python.org/packages/source/p/pip/pip-1.5.4.tar.gz"
PIP_MD5 = "834b2904f92d46aaa333267fb1c922bb"

SETUPTOOLS_URL = "https://pypi.python.org/packages/source/s/setuptools/setuptools-3.4.3.tar.gz"
SETUPTOOLS_MD5 = "284bf84819c0f6735c853619d1a54955"

def mkdir_p(path):
    # Create a directory using mkdir -p
    # Solution provided on StackOverflow
    try:
        os.makedirs(path)
    except OSError as exc:
        if not(exc.errno == errno.EEXIST and os.path.isdir(path)):
            raise


def make_executable(filename):
    st = os.stat(filename)
    os.chmod(filename, st.st_mode | stat.S_IEXEC)


def get_casapy_path():
    casapy_path = find_executable('casapy')
    if casapy_path is None:
        raise SystemError("Could not locate casapy command")
    casapy_path = os.path.realpath(casapy_path)
    if not os.path.exists(casapy_path):
        raise SystemError("The casapy command does not point to a valid CASA installation")
    return casapy_path


def get_python_version_mac(casapy_path=None):
    if casapy_path is None:
        casapy_path = get_casapy_path()
    parent = os.path.dirname(casapy_path)
    python = os.path.join(parent, 'python')
    p = subprocess.Popen([python, '--version'], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    p.wait()
    version = p.stderr.read().split()[1][:3]
    print("Determined Python version in CASA... {0}".format(version))
    return version

def get_python_path_linux(casapy_path=None):
    """ get the version and the appropriate parent directory path """
    if casapy_path is None:
        casapy_path = get_casapy_path()
    parent = os.path.dirname(casapy_path)
    grandparent = os.path.dirname(parent)
    if os.path.exists(os.path.join(grandparent, 'lib64', 'python2.6')):
        version = "2.6"
        path = grandparent
    elif os.path.exists(os.path.join(grandparent, 'lib64', 'python2.7')):
        version = "2.7"
        path = grandparent
    elif os.path.exists(os.path.join(parent, 'lib64', 'python2.6')):
        version = "2.6"
        path = parent
    elif os.path.exists(os.path.join(parent, 'lib64', 'python2.7')):
        version = "2.7"
        path = parent
    else:
        raise ValueError("Could not determine Python version")
    return version,path

def get_python_version_linux(casapy_path=None):
    version,casapy_parent_path = get_python_path_linux(casapy_path=casapy_path)
    print("Determined Python version in CASA... {0}".format(version))
    return version


def install_package(pv="2.7",packagename='pip',url=PIP_URL,md5_checksum=PIP_MD5):

    print("Downloading {0}...".format(packagename))

    # Create temporary directory

    tmpdir = tempfile.mkdtemp()
    os.chdir(tmpdir)

    # Download module and expand

    content = urlopen(url).read()

    if md5(content).hexdigest() != md5_checksum:
        raise ValueError("checksum does not match")

    f = open(os.path.basename(url), 'wb')
    f.write(content)
    f.close()

    # Prepare installation script

    print("Installing {0}...".format(packagename))

    site_packages = os.path.expanduser('~/.casa/lib/python{pv}/site-packages'.format(pv=pv))
    mkdir_p(site_packages)

    PKG_INSTALL = """
#!/bin/bash
export PYTHONUSERBASE=$HOME/.casa
export PATH=$HOME/.casa/bin:$PATH
tar xvzf {pkg_filename}
cd {pkg_name}
casa-python setup.py install --prefix=$HOME/.casa
    """

    pkg_filename = os.path.basename(url)
    pkg_name = pkg_filename.rsplit('.', 2)[0]

    f = open('install_pkg.sh', 'w')
    f.write(PKG_INSTALL.format(pkg_filename=pkg_filename, pkg_name=pkg_name))
    f.close()

    make_executable('install_pkg.sh')

    # Need to use subprocess instead
    retcode = os.system('./install_pkg.sh')
    if retcode != 0:
        raise SystemError("{0} installation failed!".format(packagename))


def write_casa_python_mac(pv="2.7", casapy_path=None):

    print("Creating casa-python script...")

    TEMPLATE_PYTHON = """
#!/bin/sh

INSTALLPATH={casapy_path}

PROOT=$INSTALLPATH/Frameworks/Python.framework/Versions/{pv}
PBIND=$PROOT/MacOS
PLIBD=$PROOT/lib/python{pv}
PPATH=$PBIND:$PLIBD:$PLIBD/plat-mac:$PLIBD/plat-darwin
PPATH=$PPATH:$PBIND/lib-scriptpackages:$PLIBD/lib-tk
PPATH=$PPATH:$PLIBD/lib-dynload:$PLIBD/site-packages
PPATH=$PPATH:$PLIBD/site-packages/Numeric:$PLIBD/site-packages/PyObjC
PPATH=$INSTALLPATH/Resources/python:$PPATH

export PYTHONUSERBASE=$HOME/.casa

export PYTHONHOME=$PROOT
export PYTHONPATH={user_site}:$PPATH
export PYTHONEXECUTABLE=$PROOT/Resources/Python.app/Contents/MacOS/Python

export DYLD_FRAMEWORK_PATH="$INSTALLPATH/Frameworks"

exec -a pythonw $INSTALLPATH/MacOS/pythonw -W ignore::DeprecationWarning "$@"
    """

    mkdir_p(BIN_DIR)

    casapy_path = os.path.dirname(os.path.dirname(get_casapy_path()),
                                  casapy_path=casapy_path)

    f = open(os.path.join(BIN_DIR, 'casa-python'), 'w')
    f.write(TEMPLATE_PYTHON.format(casapy_path=casapy_path, pv=pv, user_site=USER_SITE.format(pv=pv)))
    f.close()

    make_executable(os.path.join(BIN_DIR, 'casa-python'))


def write_casa_python_linux(pv="2.7", casapy_path=None):

    print("Creating casa-python script...")

    TEMPLATE_PYTHON = """
#!/bin/sh

INSTALLPATH={casapy_path}

export LD_LIBRARY_PATH=$INSTALLPATH/lib64:/lib64:/usr/lib64:$LD_LIBRARY_PATH
export LDFLAGS="-L$INSTALLPATH/lib64/"

export PYTHONHOME=$INSTALLPATH

export PYTHONUSERBASE=$HOME/.casa

export PYTHONPATH=$INSTALLPATH/lib64/python{pv}/site-packages:$PYTHONPATH
export PYTHONPATH=$INSTALLPATH/lib64/python{pv}/heuristics:$PYTHONPATH
export PYTHONPATH=$INSTALLPATH/lib64/python{pv}:$PYTHONPATH

exec $INSTALLPATH/lib64/casapy/bin/python $*
    """

    mkdir_p(BIN_DIR)

    # vers is throwaway here
    vers,casapy_path = get_python_path_linux(casapy_path=casapy_path)

    f = open(os.path.join(BIN_DIR, 'casa-python'), 'w')
    f.write(TEMPLATE_PYTHON.format(casapy_path=casapy_path, pv=pv))
    f.close()

    make_executable(os.path.join(BIN_DIR, 'casa-python'))


def write_casa_pip():

    print("Creating casa-pip script...")

    TEMPLATE_PIP = """
$HOME/.casa/bin/casa-python $HOME/.casa/bin/pip $* --user
    """

    f = open(os.path.join(BIN_DIR, 'casa-pip'), 'w')
    f.write(TEMPLATE_PIP)
    f.close()

    make_executable(os.path.join(BIN_DIR, 'casa-pip'))


def write_init(pv="2.7"):

    print("Creating init.py script...")

    TEMPLATE_INIT = """
import site
site.addsitedir("{site_packages}")
    """

    f = open(os.path.join(USER_DIR, 'init.py'), 'a')
    f.write(TEMPLATE_INIT.format(site_packages=USER_SITE.format(pv=pv)))
    f.close()


def add_bin_to_path():
    # TODO: make this happne in future
    print("You should now add {0} to your PATH".format(BIN_DIR))


if __name__ == "__main__":

    parser = optparse.OptionParser()
    parser.add_option('-p','--casapy_path',dest='casapy_path',
                      help='Full path to the casapy executable', default=None)
    options, args = parser.parse_args()

    if platform.system() == 'Darwin':

        python_version = get_python_version_mac(casapy_path=options.casapy_path)
        write_casa_python_mac(pv=python_version, casapy_path=options.casapy_path)

    else:

        python_version = get_python_version_linux(casapy_path=options.casapy_path)
        write_casa_python_linux(pv=python_version, casapy_path=options.casapy_path)


    install_package(pv=python_version, packagename='setuptools',
                    url=SETUPTOOLS_URL, md5_checksum=SETUPTOOLS_MD5)
    install_package(pv=python_version, packagename='pip', url=PIP_URL,
                    md5_checksum=PIP_MD5)
    write_casa_pip()
    write_init(pv=python_version)

    add_bin_to_path()
