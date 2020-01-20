"""
Small utility script used to manipulate and refactor presets.
"""


from __future__ import absolute_import, print_function, unicode_literals

import argparse
import os
from collections import OrderedDict

from build_swift.build_swift import driver_arguments
from build_swift.build_swift import shell
from build_swift.build_swift.presets import Preset, PresetParser


# -----------------------------------------------------------------------------
# Constants

UTILS_DIR = os.path.abspath(os.path.dirname(__file__))

DEFAULT_PRESET_FILES = [
    os.path.join(UTILS_DIR, 'build-presets.ini'),
]


# -----------------------------------------------------------------------------
# Helpers

def _diff_namespaces(namespace_a, namespace_b):
    """Returns the set difference of namespace_a to namespace_b (a - b).
    """

    dict_a = vars(namespace_a)
    dict_b = vars(namespace_b)

    all_keys = set(dict_a.keys()) | set(dict_b.keys())

    diff = dict()
    for key in all_keys:
        if key in dict_a and key in dict_b:
            value_a = dict_a[key]
            value_b = dict_b[key]
            if value_a != value_b:
                diff[key] = value_b

        elif key in dict_b:
            diff[key] = dict_b[key]

    return diff


def _print_args(args, indent=0):
    for arg in args:
        print(' ' * indent + shell.quote(arg))


def _print_dict(dict, indent=0):
    for key in sorted(dict.keys()):
        print(' ' * indent + '{}: {!r}'.format(key, dict[key]))


def _diff_presets(preset_a, preset_b):
    """
    """

    arg_parser = driver_arguments.create_argument_parser()

    (a_args, a_unknown) = arg_parser.parse_known_args(preset_a.args)
    (b_args, b_unknown) = arg_parser.parse_known_args(preset_b.args)

    ab_namespace_diff = _diff_namespaces(a_args, b_args)
    ba_namespace_diff = _diff_namespaces(b_args, a_args)

    if len(ab_namespace_diff) > 0:
        print('Parsed argument namespace diff ("{}" - "{}"):'.format(
            preset_a.name, preset_b.name))
        _print_dict(ab_namespace_diff, indent=4)
        print()

    if len(ba_namespace_diff) > 0:
        print('Parsed argument namespace diff ("{}" - "{}"):'.format(
            preset_b.name, preset_a.name))
        _print_dict(ba_namespace_diff, indent=4)
        print()

    if a_unknown != b_unknown:
        print('Preset "{}" build-script-impl args:'.format(preset_a.name))
        _print_args(a_unknown, indent=4)
        print()

        print('Preset "{}" build-script-impl args:'.format(preset_b.name))
        _print_args(b_unknown, indent=4)


def _simplify_preset(preset):
    """
    """

    simplified_options = OrderedDict()
    for (name, value) in preset.options:
        # Remove previously defined arg to preserve ordering
        if name in simplified_options:
            del simplified_options[name]

        simplified_options[name] = value

    return Preset(preset.name, simplified_options.items())


def _format_preset(preset):
    """
    """

    preset_str = '[preset: {}]\n'.format(preset.name)
    for (name, value) in preset.options:
        if value is None:
            preset_str += '{}\n'.format(name)
        else:
            preset_str += '{}={}\n'.format(name, value)

    return preset_str


def _print_preset(preset):
    """
    """

    print(_format_preset(preset))


# -----------------------------------------------------------------------------
# Subcommands

def diff_presets(args):
    """
    """

    parser = PresetParser()
    parser.read_files(args.preset_files)

    preset_a = parser.get_preset(args.preset_a, raw=True)
    preset_b = parser.get_preset(args.preset_b, raw=True)

    _diff_presets(preset_a, preset_b)


def expand_preset(args):
    """
    """

    parser = PresetParser()
    parser.read_files(args.preset_files)

    preset = parser.get_preset(args.preset, raw=True)

    join_str = ' '
    if args.split_lines:
        join_str = '\n'

    # Quote args for safety
    quoted_args = [shell.quote(arg) for arg in preset.args]

    print(join_str.join(quoted_args))


def list_presets(args):
    """
    """

    parser = PresetParser()
    parser.read_files(args.preset_files)

    for name in parser.preset_names:
        print(name)


def simplify_preset(args):
    """
    """

    parser = PresetParser()
    parser.read_files(args.preset_files)

    original = parser.get_preset(args.preset, raw=True)

    simplified = _simplify_preset(original)

    _print_preset(simplified)


# -----------------------------------------------------------------------------

def parse_args():
    parser = argparse.ArgumentParser(version='0.1.0')

    parser.set_defaults(preset_files=DEFAULT_PRESET_FILES)

    parser.add_argument('--preset-file',
                        dest='preset_files',
                        action='append',
                        metavar='PATH',
                        help='File containing preset definitions (multiple '
                             'uses append)')

    subparsers = parser.add_subparsers(dest='subparser_name')

    # -------------------------------------------------------------------------
    # Diff Subcommand

    diff_parser = subparsers.add_parser('diff')
    diff_parser.set_defaults(func=diff_presets)

    diff_parser.add_argument('preset_a',
                             help='First preset name')
    diff_parser.add_argument('preset_b',
                             help='Second preset name')

    # -------------------------------------------------------------------------
    # Expand Subcommand

    expand_parser = subparsers.add_parser('expand')
    expand_parser.set_defaults(func=expand_preset)

    expand_parser.add_argument('preset',
                               help='Preset name')

    expand_parser.add_argument('--split-lines',
                               action='store_true',
                               help='Split preset arguments into separate '
                                    'lines')

    # -------------------------------------------------------------------------
    # List Subcommand

    list_parser = subparsers.add_parser('list')
    list_parser.set_defaults(func=list_presets)

    # -------------------------------------------------------------------------
    # Simplify Subcommand

    simplify_parser = subparsers.add_parser('simplify')
    simplify_parser.set_defaults(func=simplify_preset)

    simplify_parser.add_argument('preset',
                                 help='Preset name')

    return parser.parse_args()


def main():
    args = parse_args()
    return args.func(args)


if __name__ == '__main__':
    main()
