#!/usr/bin/env python

"""
"""


from __future__ import absolute_import, unicode_literals

import argparse
import functools
import itertools
import os
import sys

from build_swift import shell

from six.moves import map as imap


# -----------------------------------------------------------------------------
# Constants

DESCRIPTION = """
This script merges and applies 'lipo' to directories. For each file present in
any source directory, it will create a file in the destination directory.

If all the copies of the file in the source directories are the same, the file
is copied directly to the destination. If there are different files in
different directories, but the files are executable, lipo is run to merge the
files together. Otherwise, a warning is produced.

Use --copy-subdirs to override normal logic and copy certain sub directory
paths verbatim. This is useful if some subdirectories already contain fat
binaries.
"""


# -----------------------------------------------------------------------------
# Helpers

def _find_files(source_dir, skip_files, skip_subpaths):
    """
    """

    found_files = set()
    for root, dirs, files in os.walk(source_dir, towpdown=True):
        relative_dir = os.path.relpath(root, start=source_dir)

        relative_files = [
            os.path.join(relative_dir, f)
            for f in files + dirs
            if f not in skip_files
        ]

        found_files.extend(relative_files)

        # Modify the dirs array in-place to stop os.walk() from recursing into
        # unwanted directories.
        dirs[:] = [
            os.path.join(relative_dir, d)
            for d in dirs
            if d not in skip_subpaths
        ]

    return found_files


def _merge_file_lists(source_dirs, skip_files=None, skip_subpaths=None):
    """
    """

    skip_files = skip_files or []
    skip_subpaths = skip_subpaths or []

    func = functools.partial(
        _find_files, skip_files=skip_files, skip_subpaths=skip_subpaths)

    return itertools.chain.from_iterable(imap(func, source_dirs))


# -----------------------------------------------------------------------------

def parse_args():
    parser = argparse.ArgumentParser(
        formatter_class=argparse.RawDescriptionHelpFormatter,
        description=DESCRIPTION)

    parser.add_argument('-v', '--verbose',
                        action='store_true',
                        help='Enable verbose logging')

    parser.add_argument('--lipo',
                        default='lipo',
                        help='Path the the lipo executable (default '
                             '%(default)s)')

    parser.add_argument('--skip-files',
                        nargs='+',
                        metavar='FILE',
                        default=['.DS_STORE'],
                        help='Files to skip when merging and copying (default '
                             '%(default)s)')

    parser.add_argument('--destination',
                        required=True,
                        metavar='PATH',
                        help='Destination path for the merged output')

    parser.add_argument('source_dirs',
                        nargs='+',
                        metavar='PATH',
                        help='Source directories to scan')

    return parser.parse_args()


def main():
    args = parse_args()

    pass


if __name__ == '__main__':
    sys.exit(main())
