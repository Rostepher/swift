# This source file is part of the Swift.org open source project
#
# Copyright (c) 2014 - 2020 Apple Inc. and the Swift project authors
# Licensed under Apache License v2.0 with Runtime Library Exception
#
# See https://swift.org/LICENSE.txt for license information
# See https://swift.org/CONTRIBUTORS.txt for the list of Swift project authors


"""
Wrappers for interacting with the CMake command line utiltiy and build system.
"""


from __future__ import absolute_import
from __future__ import unicode_literals

import re
from collections import OrderedDict

import six

from .. import class_utils
from .. import shell
from ..versions import Version


__all__ = [
    "CMakeCache",
    "CMakeCacheEntry",
    "CMakeValueType",
    "CMakeWrapper",
]


# --------------------------------------------------------------------------------------
# Constants


_TRUTHY_VALUES = ["TRUE", "ON", "YES", "Y"]
_FALSEY_VALUES = ["0", "FALSE", "OFF", "NO", "N", "IGNORE", "NOTFOUND"]

_NOTFOUND_SUFFIX = "-NOTFOUND"

_VERSION_PATTERN = re.compile(
    r"^cmake version (?P<version>[0-9.]+)$", flags=re.MULTILINE
)


# --------------------------------------------------------------------------------------
# Helpers


def _is_truthy(value):
    """True values are the strings: ON, YES, Y, TRUE or any non-zero number.
    """

    value = six.text_type(value).upper()
    if value in _TRUTHY_VALUES:
        return True

    try:
        return int(value) != 0
    except ValueError:
        return False


def _is_falsey(value):
    """False values are the strings: OFF, NO, N, FALSE, IGNORE, NOTFOUND, the
    empty string, the constant 0 or any string that ends with the suffix
    -NOTFOUND.
    """

    value = six.text_type(value).upper()
    return value == "" or value in _FALSEY_VALUES or value.endswith(_NOTFOUND_SUFFIX)


def _cmake_bool(value):
    """Helper function used to validate a CMake bool and return a Python bool.
    Raises a value error if the input value is neither truthy nor falsey.
    """

    if _is_truthy(value):
        return True
    elif _is_falsey(value):
        return False

    raise ValueError("Invalid bool value: {}".format(value))


@class_utils.generate_repr("value")
class _ValueWrapper(object):
    """Wrapper object around a given value.
    """

    __slots__ = "value"

    def __init__(self, value):
        self.value = value

    def __eq__(self, other):
        if not isinstance(other, type(self)):
            return NotImplemented

        return self.value == other.value

    def __ne__(self, other):
        return not self == other

    def __str__(self):
        return six.text_type(self.value)


class _BoolWrapper(_ValueWrapper):
    """Wrapper object around a CMake bool value. Upon instantiation the value
    is validated as a truthy or falsey value.
    """

    __slots__ = ()

    def __init__(self, value):
        self.value = _cmake_bool(value)

    def __str__(self):
        return six.text_type(self.value).upper()


class _ListWrapper(_ValueWrapper):
    """Wrapper object around a CMake list value. Upon instantiation the value
    is validated as a list instance.
    """

    __slots__ = ()

    def __init__(self, value):
        if not isinstance(value, list):
            raise ValueError("Invalid list value: {}".format(repr(value)))

        self.value = value

    def __str__(self):
        return ";".join([six.text_type(item) for item in self.value])


# --------------------------------------------------------------------------------------
# CMake Value Types


class CMakeValueType(object):
    """Poor-mans's enum used to represent the full range of valid CMake value
    types.
    """

    __slots__ = "name"

    __members__ = []

    def __init__(self, name):
        self.name = name

    def __eq__(self, other):
        if not isinstance(other, CMakeValueType):
            return NotImplemented

        return self.name == other.name

    def __ne__(self, other):
        return not self == other

    def __hash__(self):
        return hash(self.name)

    def __str__(self):
        return self.name

    def __repr__(self):
        return "{}.{}".format(type(self).__name__, self.name)

    @classmethod
    def _register(cls, name):
        member = cls(name)
        if member in cls.__members__:
            return

        cls.__members__.append(member)
        setattr(cls, name, member)

    @classmethod
    def from_name(cls, name):
        for member in cls.__members__:
            if member.name == name:
                return member

        raise ValueError('Unknown value type "{}"'.format(name))


CMakeValueType._register("BOOL")
CMakeValueType._register("FILEPATH")
CMakeValueType._register("PATH")
CMakeValueType._register("STRING")
CMakeValueType._register("INTERNAL")


# --------------------------------------------------------------------------------------
# CMake Cache


@class_utils.generate_repr("name", "value", "value_type")
class CMakeCacheEntry(object):
    """Class representing a single entry in a CMake cache.

    Each entry is composed of a name, value and optionally a value type. Value
    types are not required by CMake and thus the default is None.
    """

    __slots__ = ("_name", "_value_wrapper", "_value_type")

    def __init__(self, name, value, value_type=None):
        if not isinstance(name, six.string_types):
            raise ValueError("Invalid name type {}".format(type(name).__name__))

        if len(name) < 1:
            raise ValueError("CMake variable names cannot be empty")

        # Lists are always treated as string value types.
        if isinstance(value, list):
            value = _ListWrapper(value)
            value_type = CMakeValueType.STRING

        elif isinstance(value, bool) or value_type == CMakeValueType.BOOL:
            value = _BoolWrapper(value)
            value_type = CMakeValueType.BOOL

        # All other values are wrapped in a generic value wrapper.
        else:
            value = _ValueWrapper(value)

        # Allow users to input value types as strings.
        if isinstance(value_type, six.string_types):
            value_type = CMakeValueType.from_name(value_type)

        self._name = name
        self._value_type = value_type
        self._value_wrapper = value

    def __key(self):
        return (self._name, self._value_wrapper, self._value_type)

    def __eq__(self, other):
        if not isinstance(other, CMakeCacheEntry):
            return NotImplemented

        return self.__key() == other.__key()

    def __ne__(self, other):
        return not self == other

    def __str__(self):
        if self.value_type is None:
            return "{}={}".format(self._name, six.text_type(self._value_wrapper))

        return "{}:{}={}".format(
            self._name, self._value_type, six.text_type(self._value_wrapper)
        )

    # ----------------------------------------------------------------------------------

    @property
    def name(self):
        return self._name

    @property
    def value(self):
        return self._value_wrapper.value

    @property
    def value_type(self):
        return self._value_type


@class_utils.generate_repr("entries")
class CMakeCache(object):
    """Class representing a CMake cache, composed of an ordered set of cache
    entries. Entries can be set and unset, but only one entry exists per
    variable name.
    """

    __slots__ = "_entries"

    def __init__(self):
        self._entries = OrderedDict()

    def __len__(self):
        return len(self._entries)

    def __iter__(self):
        return iter(self._entries.values())

    def __contains__(self, name):
        return name in self._entries

    def __getitem__(self, key):
        return self._entries[key]

    def __setitem__(self, key, value):
        self.set(key, value)

    def __delitem__(self, key):
        self.unset(key)

    def __add__(self, other):
        if not isinstance(other, type(self)):
            raise TypeError("Invalid type {}".format(type(other).__name__))

        new_cache = CMakeCache()
        new_cache += self
        new_cache += other
        return new_cache

    def __iadd__(self, other):
        if not isinstance(other, type(self)):
            raise TypeError("Invalid type {}".format(type(other).__name__))

        self._entries.update(other._entries)
        return self

    # ----------------------------------------------------------------------------------

    @property
    def entries(self):
        """Returns a list of cache entries in the order they were set.
        """

        return self._entries.values()

    @property
    def args(self):
        """Returns an list of cache entries formatted as command line arguments
        in the order they were set.
        """

        return ["-D{}".format(entry) for entry in self.entries]

    def get(self, name, default=None):
        """Returns the entry for the given name. If the entry does not exist
        the default value is returned.
        """

        return self._entries.get(name, default)

    def set(self, name, value, value_type=None):
        """Defines a new cache entry for the given name, mapping to the
        value. If a type is provided the type is stored.
        """

        self._entries[name] = CMakeCacheEntry(name, value, value_type)

    def unset(self, name):
        """Removes a cache entry. If the entry does not exist a KeyError is
        raised.
        """

        self._entries.pop(name)

    def clear(self):
        """Clears all entries from the cache instance.
        """

        self._entries.clear()


# --------------------------------------------------------------------------------------
# CMake Wrapper


class CMakeWrapper(shell.AbstractWrapper):
    """Wrapper class around the 'cmake' command-line utility.
    """

    # ----------------------------------------------------------------------------------
    # Cache API

    Cache = CMakeCache
    ValueType = CMakeValueType

    # ----------------------------------------------------------------------------------

    def __init__(self, executable=None):
        self._executable = executable or shell.which("cmake") or "cmake"

    def Popen(self, args, **kwargs):
        return super(CMakeWrapper, self).Popen(args, **kwargs)

    def call(self, args, **kwargs):
        return super(CMakeWrapper, self).call(args, **kwargs)

    def check_call(self, args, **kwargs):
        return super(CMakeWrapper, self).check_call(args, **kwargs)

    def check_output(self, args, **kwargs):
        return super(CMakeWrapper, self).check_output(args, **kwargs)

    # ----------------------------------------------------------------------------------

    @property
    def command(self):
        """Returns the wrapper command.
        """

        return [self._executable]

    @property
    def executable(self):
        return self._executable

    @property
    def version(self):
        """Returns the cmake version.
        """

        output = self.check_output("--version")
        matches = _VERSION_PATTERN.match(output.rstrip())
        if matches:
            return Version(matches.group("version"))

        return None
