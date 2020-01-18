# This source file is part of the Swift.org open source project
#
# Copyright (c) 2014 - 2017 Apple Inc. and the Swift project authors
# Licensed under Apache License v2.0 with Runtime Library Exception
#
# See https://swift.org/LICENSE.txt for license information
# See https://swift.org/CONTRIBUTORS.txt for the list of Swift project authors


"""
CMake product and product builder.
"""


from __future__ import absolute_import, unicode_literals

import os.path
import re

from build_swift.build_swift import cache_utils
from build_swift.build_swift import shell
from build_swift.build_swift.versions import Version

from . import product


# ----------------------------------------------------------------------------
# Constants

_CMAKE_VERSION_MAJOR_PATTERN = re.compile(
    r'^set\(CMake_VERSION_MAJOR (?P<major_version>\d+)\)$')

_CMAKE_VERSION_MINOR_PATTERN = re.compile(
    r'^set\(CMake_VERSION_MINOR (?P<minor_version>\d+)\)$')

_CMAKE_VERSION_PATCH_PATTERN = re.compile(
    r'^set\(CMake_VERSION_PATCH (?P<patch_version>\d+)\)$')


# ----------------------------------------------------------------------------
# Helpers

@cache_utils.cache
def _find_cmake_source_version(source_dir):
    """
    """

    version_file = os.path.join(source_dir, 'Source', 'CMakeVersion.cmake')
    if not os.path.isfile(version_file):
        return None

    major = minor = patch = None

    with open(version_file, 'r') as f:
        for line in f.readlines():
            line = line.strip()

            matches = _CMAKE_VERSION_MAJOR_PATTERN.match(line)
            if matches:
                major = matches.group('major_version')
                continue

            matches = _CMAKE_VERSION_MINOR_PATTERN.match(line)
            if matches:
                minor = matches.group('minor_version')
                continue

            matches = _CMAKE_VERSION_PATCH_PATTERN.match(line)
            if matches:
                patch = matches.group('patch_version')
                continue

            # All components have been found!
            if major and minor and patch:
                break

    if not major or not minor or not patch:
        return None

    return Version('{}.{}.{}'.format(major, minor, patch))


# ----------------------------------------------------------------------------
# Product and ProductBuilder

class CMake(product.Product):
    """
    """

    @classmethod
    def is_build_script_impl_product(cls):
        return False

    @classmethod
    def builder(cls, args, toolchain, workspace):
        return CMakeBuilder(cls, args, toolchain, workspace)


class CMakeBuilder(product.ProductBuilder):
    """
    """

    def __init__(self, product_class, args, toolchain, workspace):
        self.args = args
        self.toolchain = toolchain
        self.workspace = workspace

        self.source_dir = workspace.source_dir(
            product_class.product_source_name())

        self.build_dir = workspace.build_dir(
            'build', product_class.product_name())

    # ------------------------------------------------------------------------

    @property
    def source_version(self):
        return _find_cmake_source_version(self.source_dir)

    @property
    def binary_path(self):
        return os.path.join(self.build_dir, 'bin', 'cmake')

    # ------------------------------------------------------------------------

    def build(self):
        if not os.path.exists(self.source_dir):
            # TODO: We should raise an error here if the source is not
            # checked out.
            pass

        if os.path.exists(self.binary_path):
            return

        bootstrap_script = os.path.join(self.source_dir, 'bootstrap')
        make_path = shell.which('make') or 'make'

        shell.makedirs(self.build_dir, echo=True)
        with shell.pushd(self.build_dir, echo=True):
            shell.check_call(
                [bootstrap_script, '--no-qt-gui'],
                echo=True)
            shell.check_call(
                [make_path, '-j', self.args.build_jobs],
                echo=True)

    def test(self):
        pass

    def install(self):
        pass
