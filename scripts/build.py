#!/usr/bin/python2.7 -u
# pylint: disable=C0301

import sys
import os
import subprocess
import time
from datetime import datetime
import shutil
import tempfile
import hashlib
import re
import logging
import argparse

# Packaging variables
PACKAGE_NAME = "influxdb-relay"
INSTALL_ROOT_DIR = "/usr/bin"
LOG_DIR = "/var/log/influxdb-relay"
DATA_DIR = "/var/lib/influxdb-relay"
SCRIPT_DIR = "/usr/lib/influxdb-relay/scripts"
CONFIG_DIR = "/etc/influxdb-relay"
LOGROTATE_DIR = "/etc/logrotate.d"

INIT_SCRIPT = "scripts/init.sh"
SYSTEMD_SCRIPT = "scripts/influxdb-relay.service"
POSTINST_SCRIPT = "scripts/post-install.sh"
POSTUNINST_SCRIPT = "scripts/post-uninstall.sh"
LOGROTATE_SCRIPT = "scripts/logrotate"
DEFAULT_CONFIG = "examples/sample.conf"

CONFIGURATION_FILES = [
    CONFIG_DIR + '/influxdb-relay.conf',
    LOGROTATE_DIR + '/influxdb-relay',
]

PACKAGE_LICENSE = "MIT"
PACKAGE_URL = "https://github.com/vente-privee/influxdb-relay"
DESCRIPTION = "Service to replicate InfluxDB data for high availability."

prereqs = ['git', 'go']
go_vet_command = "go tool vet -composites=true ./"
optional_prereqs = ['fpm', 'rpmbuild']

fpm_common_args = "-f -s dir --log error \
--url {} \
--after-install {} \
--after-remove {} \
--license {} \
--directories {} \
--directories {} \
--description \"{}\"".format(
    PACKAGE_URL,
    POSTINST_SCRIPT,
    POSTUNINST_SCRIPT,
    PACKAGE_LICENSE,
    LOG_DIR,
    DATA_DIR,
    DESCRIPTION)

for f in CONFIGURATION_FILES:
    fpm_common_args += " --config-files {}".format(f)

targets = {
    'influxdb-relay' : './main.go'
}

supported_builds = {
    'darwin': ['amd64'],
    'linux': ['amd64', 'static_amd64']
}

supported_packages = {
    "darwin": ['tar'],
    "linux": ['deb', 'rpm', 'tar']
}

def print_banner():
    logging.info(r"""
  ___       __ _          ___  ___     ___     _
 |_ _|_ _  / _| |_  ___ _|   \| _ )___| _ \___| |__ _ _  _
  | || ' \|  _| | || \ \ / |) | _ \___|   / -_) / _` | || |
 |___|_||_|_| |_|\_,_/_\_\___/|___/   |_|_\___|_\__,_|\_, |
                                                      |__/
  Build Script
""")

def create_package_fs(build_root):
    """Create a filesystem structure to mimic the package filesystem.
    """
    logging.debug("Creating package filesystem at location: {}".format(build_root))
    # Using [1:] for the path names due to them being absolute
    # (will overwrite previous paths, per 'os.path.join' documentation)
    dirs = [INSTALL_ROOT_DIR[1:],
            LOG_DIR[1:],
            DATA_DIR[1:],
            SCRIPT_DIR[1:],
            CONFIG_DIR[1:],
            LOGROTATE_DIR[1:]]
    for d in dirs:
        os.makedirs(os.path.join(build_root, d))
        os.chmod(os.path.join(build_root, d), 0o755)

def package_scripts(build_root, config_only=False):
    """Copy the necessary scripts and configuration files to the package
    filesystem.
    """
    if config_only:
        logging.debug("Copying configuration to build directory.")
        shutil.copyfile(DEFAULT_CONFIG, os.path.join(build_root, "influxdb-relay.conf"))
        os.chmod(os.path.join(build_root, "influxdb-relay.conf"), 0o644)
    else:
        logging.debug("Copying scripts and sample configuration to build directory.")
        shutil.copyfile(INIT_SCRIPT, os.path.join(build_root, SCRIPT_DIR[1:], INIT_SCRIPT.split('/')[1]))
        os.chmod(os.path.join(build_root, SCRIPT_DIR[1:], INIT_SCRIPT.split('/')[1]), 0o644)
        shutil.copyfile(SYSTEMD_SCRIPT, os.path.join(build_root, SCRIPT_DIR[1:], SYSTEMD_SCRIPT.split('/')[1]))
        os.chmod(os.path.join(build_root, SCRIPT_DIR[1:], SYSTEMD_SCRIPT.split('/')[1]), 0o644)
        shutil.copyfile(LOGROTATE_SCRIPT, os.path.join(build_root, LOGROTATE_DIR[1:], "influxdb-relay"))
        os.chmod(os.path.join(build_root, LOGROTATE_DIR[1:], "influxdb-relay"), 0o644)
        shutil.copyfile(DEFAULT_CONFIG, os.path.join(build_root, CONFIG_DIR[1:], "influxdb-relay.conf"))
        os.chmod(os.path.join(build_root, CONFIG_DIR[1:], "influxdb-relay.conf"), 0o644)

def go_get(branch, update=False, no_uncommitted=False):
    """Retrieve build dependencies or restore pinned dependencies.
    """
    if local_changes() and no_uncommitted:
        logging.error("There are uncommitted changes in the current directory.")
        return False
    return True

def run(command, allow_failure=False, shell=False):
    """Run shell command (convenience wrapper around subprocess).
    """
    out = None
    logging.debug("{}".format(command))
    try:
        if shell:
            out = subprocess.check_output(command, stderr=subprocess.STDOUT, shell=shell)
        else:
            out = subprocess.check_output(command.split(), stderr=subprocess.STDOUT)
        out = out.decode('utf-8').strip()
        # logging.debug("Command output: {}".format(out))
    except subprocess.CalledProcessError as e:
        if allow_failure:
            logging.warn("Command '{}' failed with error: {}".format(command, e.output))
            return None
        else:
            logging.error("Command '{}' failed with error: {}".format(command, e.output))
            sys.exit(1)
    except OSError as e:
        if allow_failure:
            logging.warn("Command '{}' failed with error: {}".format(command, e))
            return out
        else:
            logging.error("Command '{}' failed with error: {}".format(command, e))
            sys.exit(1)
    else:
        return out

def create_temp_dir(prefix=None):
    """ Create temporary directory with optional prefix.
    """
    if prefix is None:
        return tempfile.mkdtemp(prefix="{}-build.".format(PACKAGE_NAME))
    else:
        return tempfile.mkdtemp(prefix=prefix)

def increment_minor_version(version):
    """Return the version with the minor version incremented and patch
    version set to zero.
    """
    ver_list = version.split('.')
    if len(ver_list) != 3:
        logging.warn("Could not determine how to increment version '{}', will just use provided version.".format(version))
        return version
    ver_list[1] = str(int(ver_list[1]) + 1)
    ver_list[2] = str(0)
    inc_version = '.'.join(ver_list)
    logging.debug("Incremented version from '{}' to '{}'.".format(version, inc_version))
    return inc_version

def get_current_version_tag():
    """Retrieve the raw git version tag.
    """
    version = run("git describe --always --tags --abbrev=0")
    return version

def get_current_version():
    """Parse version information from git tag output.
    """
    version_tag = get_current_commit(short=True)
    return version_tag

def get_current_commit(short=False):
    """Retrieve the current git commit.
    """
    command = None
    if short:
        command = "git log --pretty=format:'%h' -n 1"
    else:
        command = "git rev-parse HEAD"
    out = run(command)
    return out.strip('\'\n\r ')

def get_current_branch():
    """Retrieve the current git branch.
    """
    command = "git rev-parse --abbrev-ref HEAD"
    out = run(command)
    return out.strip()

def local_changes():
    """Return True if there are local un-committed changes.
    """
    output = run("git diff-files --ignore-submodules --").strip()
    if len(output) > 0:
        return True
    return False

def get_system_arch():
    """Retrieve current system architecture.
    """
    arch = os.uname()[4]
    if arch == "x86_64":
        arch = "amd64"
    elif arch == "386":
        arch = "i386"
    elif 'arm' in arch:
        # Prevent uname from reporting full ARM arch (eg 'armv7l')
        arch = "arm"
    return arch

def get_system_platform():
    """Retrieve current system platform.
    """
    if sys.platform.startswith("linux"):
        return "linux"
    else:
        return sys.platform

def get_go_version():
    """Retrieve version information for Go.
    """
    out = run("go version")
    matches = re.search('go version go(\S+)', out)
    if matches is not None:
        return matches.groups()[0].strip()
    return None

def check_path_for(b):
    """Check the the user's path for the provided binary.
    """
    def is_exe(fpath):
        return os.path.isfile(fpath) and os.access(fpath, os.X_OK)

    for path in os.environ["PATH"].split(os.pathsep):
        path = path.strip('"')
        full_path = os.path.join(path, b)
        if os.path.isfile(full_path) and os.access(full_path, os.X_OK):
            return full_path

def check_environ(build_dir = None):
    """Check environment for common Go variables.
    """
    logging.info("Checking environment...")
    for v in [ "GOPATH", "GOBIN", "GOROOT" ]:
        logging.debug("Using '{}' for {}".format(os.environ.get(v), v))

    cwd = os.getcwd()
    if build_dir is None and os.environ.get("GOPATH") and os.environ.get("GOPATH") not in cwd:
        logging.warn("Your current directory is not under your GOPATH. This may lead to build failures.")
    return True

def check_prereqs():
    """Check user path for required dependencies.
    """
    logging.info("Checking for dependencies...")
    for req in prereqs:
        if not check_path_for(req):
            logging.error("Could not find dependency: {}".format(req))
            return False
    return True

def go_list(vendor=False, relative=False):
    """
    Return a list of packages
    If vendor is False vendor package are not included
    If relative is True the package prefix defined by PACKAGE_URL is stripped
    """
    p = subprocess.Popen(["go", "list", "./..."], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    out, err = p.communicate()
    packages = out.split('\n')
    if packages[-1] == '':
        packages = packages[:-1]
    if not vendor:
        non_vendor = []
        for p in packages:
            if '/vendor/' not in p:
                non_vendor.append(p)
        packages = non_vendor
    if relative:
        relative_pkgs = []
        for p in packages:
            r = p.replace(PACKAGE_URL, '.')
            if r != '.':
                relative_pkgs.append(r)
        packages = relative_pkgs
    return packages

def build(version=None,
          platform=None,
          arch=None,
          nightly=False,
          clean=False,
          outdir=".",
          tags=[],
          static=False):
    """Build each target for the specified architecture and platform.
    """
    logging.info("Starting build for {}/{}...".format(platform, arch))
    logging.info("Using Go version: {}".format(get_go_version()))
    logging.info("Using git branch: {}".format(get_current_branch()))
    logging.info("Using git commit: {}".format(get_current_commit()))
    if static:
        logging.info("Using statically-compiled output.")
    if len(tags) > 0:
        logging.info("Using build tags: {}".format(','.join(tags)))

    logging.info("Sending build output to: {}".format(outdir))
    if not os.path.exists(outdir):
        os.makedirs(outdir)
    elif clean and outdir != '/' and outdir != ".":
        logging.info("Cleaning build directory '{}' before building.".format(outdir))
        shutil.rmtree(outdir)
        os.makedirs(outdir)

    logging.info("Using version '{}' for build.".format(version))

    tmp_build_dir = create_temp_dir()
    for target, path in targets.items():
        logging.info("Building target: {}".format(target))
        build_command = ""

        # Handle static binary output
        if static is True or "static_" in arch:
            if "static_" in arch:
                static = True
                arch = arch.replace("static_", "")
            build_command += "CGO_ENABLED=0 "

        # Handle variations in architecture output
        if arch == "i386" or arch == "i686":
            arch = "386"
        elif "arm" in arch:
            arch = "arm"
        build_command += "GOOS={} GOARCH={} ".format(platform, arch)

        if "arm" in arch:
            if arch == "armel":
                build_command += "GOARM=5 "
            elif arch == "armhf" or arch == "arm":
                build_command += "GOARM=6 "
            elif arch == "arm64":
                # TODO(rossmcdonald) - Verify this is the correct setting for arm64
                build_command += "GOARM=7 "
            else:
                logging.error("Invalid ARM architecture specified: {}".format(arch))
                logging.error("Please specify either 'armel', 'armhf', or 'arm64'.")
                return False
        if platform == 'windows':
            target = target + '.exe'
        build_command += "go build -o {} ".format(os.path.join(outdir, target))
        if len(tags) > 0:
            build_command += "-tags {} ".format(','.join(tags))
        if "1.4" in get_go_version():
            if static:
                build_command += "-ldflags=\"-s -X main.version {} -X main.branch {} -X main.commit {}\" ".format(version,
                                                                                                                  get_current_branch(),
                                                                                                                  get_current_commit())
            else:
                build_command += "-ldflags=\"-X main.version {} -X main.branch {} -X main.commit {}\" ".format(version,
                                                                                                               get_current_branch(),
                                                                                                               get_current_commit())

        else:
            # Starting with Go 1.5, the linker flag arguments changed to 'name=value' from 'name value'
            if static:
                build_command += "-ldflags=\"-s -X main.version={} -X main.branch={} -X main.commit={}\" ".format(version,
                                                                                                                  get_current_branch(),
                                                                                                                  get_current_commit())
            else:
                build_command += "-ldflags=\"-X main.version={} -X main.branch={} -X main.commit={}\" ".format(version,
                                                                                                               get_current_branch(),
                                                                                                               get_current_commit())
        if static:
            build_command += "-a -installsuffix cgo "
        build_command += path
        start_time = datetime.utcnow()
        run(build_command, shell=True)
        end_time = datetime.utcnow()
        logging.info("Time taken: {}s".format((end_time - start_time).total_seconds()))
    return True

def generate_md5_from_file(path):
    """Generate MD5 signature based on the contents of the file at path.
    """
    m = hashlib.md5()
    with open(path, 'rb') as f:
        for chunk in iter(lambda: f.read(4096), b""):
            m.update(chunk)
    return m.hexdigest()

def package(build_output, version, nightly=False, iteration=1, static=False, release=False):
    """Package the output of the build process.
    """
    outfiles = []
    tmp_build_dir = create_temp_dir()
    logging.debug("Packaging for build output: {}".format(build_output))
    logging.info("Using temporary directory: {}".format(tmp_build_dir))
    try:
        for platform in build_output:
            # Create top-level folder displaying which platform (linux, etc)
            os.makedirs(os.path.join(tmp_build_dir, platform))
            for arch in build_output[platform]:
                logging.info("Creating packages for {}/{}".format(platform, arch))
                # Create second-level directory displaying the architecture (amd64, etc)
                current_location = build_output[platform][arch]

                # Create directory tree to mimic file system of package
                build_root = os.path.join(tmp_build_dir,
                                          platform,
                                          arch,
                                          '{}-{}-{}'.format(PACKAGE_NAME, version, iteration))
                os.makedirs(build_root)

                # Copy packaging scripts to build directory
                if platform == "windows" or static or "static_" in arch:
                    # For windows and static builds, just copy
                    # binaries to root of package (no other scripts or
                    # directories)
                    package_scripts(build_root, config_only=True)
                else:
                    create_package_fs(build_root)
                    package_scripts(build_root)

                for binary in targets:
                    # Copy newly-built binaries to packaging directory
                    if platform == 'windows':
                        binary = binary + '.exe'
                    if platform == 'windows' or static or "static_" in arch:
                        # Where the binary should go in the package filesystem
                        to = os.path.join(build_root, binary)
                        # Where the binary currently is located
                        fr = os.path.join(current_location, binary)
                    else:
                        # Where the binary currently is located
                        fr = os.path.join(current_location, binary)
                        # Where the binary should go in the package filesystem
                        to = os.path.join(build_root, INSTALL_ROOT_DIR[1:], binary)
                    shutil.copy(fr, to)

                for package_type in supported_packages[platform]:
                    # Package the directory structure for each package type for the platform
                    logging.debug("Packaging directory '{}' as '{}'.".format(build_root, package_type))
                    name = PACKAGE_NAME
                    # Reset version, iteration, and current location on each run
                    # since they may be modified below.
                    package_version = "{}".format(version)
                    package_iteration = iteration
                    if "static_" in arch:
                        # Remove the "static_" from the displayed arch on the package
                        package_arch = arch.replace("static_", "")
                    else:
                        package_arch = arch
                    package_build_root = build_root
                    current_location = build_output[platform][arch]
                    if package_type in ['zip', 'tar']:
                        # For tars and zips, start the packaging one folder above
                        # the build root (to include the package name)
                        package_build_root = os.path.join('/', '/'.join(build_root.split('/')[:-1]))
                        if nightly:
                            if static or "static_" in arch:
                                name = '{}-static-nightly_{}_{}'.format(name,
                                                                        platform,
                                                                        package_arch)
                            else:
                                name = '{}-nightly_{}_{}'.format(name,
                                                                 platform,
                                                                 package_arch)
                        else:
                            if static or "static_" in arch:
                                name = '{}-{}-{}-static_{}_{}'.format(name,
                                                                      package_version,
                                                                      package_iteration,
                                                                      platform,
                                                                      package_arch)
                            else:
                                name = '{}-{}-{}_{}_{}'.format(name,
                                                               package_version,
                                                               package_iteration,
                                                               platform,
                                                               package_arch)
                        current_location = os.path.join(os.getcwd(), current_location)
                        if package_type == 'tar':
                            tar_command = "cd {} && tar -cvzf {}.tar.gz ./*".format(build_root, name)
                            run(tar_command, shell=True)
                            run("mv {}.tar.gz {}".format(os.path.join(build_root, name), current_location), shell=True)
                            outfile = os.path.join(current_location, name + ".tar.gz")
                            outfiles.append(outfile)
                        elif package_type == 'zip':
                            zip_command = "cd {} && zip -r {}.zip ./*".format(build_root, name)
                            run(zip_command, shell=True)
                            run("mv {}.zip {}".format(os.path.join(build_root, name), current_location), shell=True)
                            outfile = os.path.join(current_location, name + ".zip")
                            outfiles.append(outfile)
                    elif package_type not in ['zip', 'tar'] and static or "static_" in arch:
                        logging.info("Skipping package type '{}' for static builds.".format(package_type))
                    else:
                        fpm_command = "fpm {} --name {} -a {} -t {} --version {} --iteration {} -C {} -p {} ".format(
                            fpm_common_args,
                            name,
                            package_arch,
                            package_type,
                            package_version,
                            package_iteration,
                            package_build_root,
                            current_location)
                        if package_type == "rpm":
                            fpm_command += "--depends coreutils --rpm-posttrans {}".format(POSTINST_SCRIPT)
                        out = run(fpm_command, shell=True)
                        matches = re.search(':path=>"(.*)"', out)
                        outfile = None
                        if matches is not None:
                            outfile = matches.groups()[0]
                        if outfile is None:
                            logging.warn("Could not determine output from packaging output!")
                        else:
                            if nightly:
                                # Strip nightly version from package name
                                new_outfile = outfile.replace("{}-{}".format(package_version, package_iteration), "nightly")
                                os.rename(outfile, new_outfile)
                                outfile = new_outfile
                            else:
                                if package_type == 'rpm':
                                    # rpm's convert any dashes to underscores
                                    package_version = package_version.replace("-", "_")
                                new_outfile = outfile.replace("{}-{}".format(package_version, package_iteration), package_version)
                                os.rename(outfile, new_outfile)
                                outfile = new_outfile
                            outfiles.append(os.path.join(os.getcwd(), outfile))
        logging.debug("Produced package files: {}".format(outfiles))
        return outfiles
    finally:
        # Cleanup
        shutil.rmtree(tmp_build_dir)

def main(args):
    global PACKAGE_NAME

    if args.release and args.nightly:
        logging.error("Cannot be both a nightly and a release.")
        return 1

    if args.nightly:
        args.version = increment_minor_version(args.version)
        args.version = "{}~n{}".format(args.version,
                                       datetime.utcnow().strftime("%Y%m%d%H%M"))
        args.iteration = 0

    # Pre-build checks
    check_environ()
    if not check_prereqs():
        return 1
    if args.build_tags is None:
        args.build_tags = []
    else:
        args.build_tags = args.build_tags.split(',')

    orig_commit = get_current_commit(short=True)
    orig_branch = get_current_branch()

    if args.platform not in supported_builds and args.platform != 'all':
        logging.error("Invalid build platform: {}".format(target_platform))
        return 1

    build_output = {}

    if args.branch != orig_branch and args.commit != orig_commit:
        logging.error("Can only specify one branch or commit to build from.")
        return 1
    elif args.branch != orig_branch:
        logging.info("Moving to git branch: {}".format(args.branch))
        run("git checkout {}".format(args.branch))
    elif args.commit != orig_commit:
        logging.info("Moving to git commit: {}".format(args.commit))
        run("git checkout {}".format(args.commit))

    if not args.no_get:
        if not go_get(args.branch, no_uncommitted=args.no_uncommitted):
            return 1

    platforms = []
    single_build = True
    if args.platform == 'all':
        platforms = supported_builds.keys()
        single_build = False
    else:
        platforms = [args.platform]

    for platform in platforms:
        build_output.update( { platform : {} } )
        archs = []
        if args.arch == "all":
            single_build = False
            archs = supported_builds.get(platform)
        else:
            archs = [args.arch]

        for arch in archs:
            od = args.outdir
            if not single_build:
                od = os.path.join(args.outdir, platform, arch)
            if not build(version=args.version,
                         platform=platform,
                         arch=arch,
                         nightly=args.nightly,
                         clean=args.clean,
                         outdir=od,
                         tags=args.build_tags,
                         static=args.static):
                return 1
            build_output.get(platform).update( { arch : od } )

    # Build packages
    if args.package:
        if not check_path_for("fpm"):
            logging.error("FPM ruby gem required for packaging. Stopping.")
            return 1
        packages = package(build_output,
                           args.version,
                           nightly=args.nightly,
                           iteration=args.iteration,
                           static=args.static,
                           release=args.release)
        logging.info("Packages created:")
        for p in packages:
            logging.info("{} (MD5={})".format(p.split('/')[-1:][0],
                                              generate_md5_from_file(p)))
    if orig_branch != get_current_branch():
        logging.info("Moving back to original git branch: {}".format(orig_branch))
        run("git checkout {}".format(orig_branch))

    return 0

if __name__ == '__main__':
    LOG_LEVEL = logging.INFO
    if '--debug' in sys.argv[1:]:
        LOG_LEVEL = logging.DEBUG
    log_format = '[%(levelname)s] %(funcName)s: %(message)s'
    logging.basicConfig(level=LOG_LEVEL,
                        format=log_format)

    parser = argparse.ArgumentParser(description='InfluxDB build and packaging script.')
    parser.add_argument('--verbose','-v','--debug',
                        action='store_true',
                        help='Use debug output')
    parser.add_argument('--outdir', '-o',
                        metavar='<output directory>',
                        default='./build/',
                        type=os.path.abspath,
                        help='Output directory')
    parser.add_argument('--name', '-n',
                        metavar='<name>',
                        type=str,
                        help='Name to use for package name (when package is specified)')
    parser.add_argument('--arch',
                        metavar='<amd64|i386|armhf|arm64|armel|all>',
                        type=str,
                        default=get_system_arch(),
                        help='Target architecture for build output')
    parser.add_argument('--platform',
                        metavar='<linux|darwin|windows|all>',
                        type=str,
                        default=get_system_platform(),
                        help='Target platform for build output')
    parser.add_argument('--branch',
                        metavar='<branch>',
                        type=str,
                        default=get_current_branch(),
                        help='Build from a specific branch')
    parser.add_argument('--commit',
                        metavar='<commit>',
                        type=str,
                        default=get_current_commit(short=True),
                        help='Build from a specific commit')
    parser.add_argument('--version',
                        metavar='<version>',
                        type=str,
                        default=get_current_version(),
                        help='Version information to apply to build output (ex: 0.1.0)')
    parser.add_argument('--iteration',
                        metavar='<package iteration>',
                        type=str,
                        default="1",
                        help='Package iteration to apply to build output (defaults to 1)')
    parser.add_argument('--nightly',
                        action='store_true',
                        help='Mark build output as nightly build (will incremement the minor version)')
    parser.add_argument('--package',
                        action='store_true',
                        help='Package binary output')
    parser.add_argument('--release',
                        action='store_true',
                        help='Mark build output as release')
    parser.add_argument('--clean',
                        action='store_true',
                        help='Clean output directory before building')
    parser.add_argument('--no-get',
                        action='store_true',
                        help='Do not retrieve pinned dependencies when building')
    parser.add_argument('--no-uncommitted',
                        action='store_true',
                        help='Fail if uncommitted changes exist in the working directory')
    parser.add_argument('--generate',
                        action='store_true',
                        help='Run "go generate" before building')
    parser.add_argument('--build-tags',
                        metavar='<tags>',
                        help='Optional build tags to use for compilation')
    parser.add_argument('--static',
                        action='store_true',
                        help='Create statically-compiled binary output')
    args = parser.parse_args()
    print_banner()
    sys.exit(main(args))
