# This source file is part of the Swift.org open source project
#
# Copyright (c) 2014 - 2020 Apple Inc. and the Swift project authors
# Licensed under Apache License v2.0 with Runtime Library Exception
#
# See https://swift.org/LICENSE.txt for license information
# See https://swift.org/CONTRIBUTORS.txt for the list of Swift project authors


from __future__ import absolute_import
from __future__ import unicode_literals

import unittest

from build_swift.wrappers.cmake import CMakeCache
from build_swift.wrappers.cmake import CMakeCacheEntry
from build_swift.wrappers.cmake import CMakeValueType
from build_swift.wrappers.cmake import CMakeWrapper
from build_swift.wrappers.cmake import _BoolWrapper
from build_swift.wrappers.cmake import _ListWrapper
from build_swift.wrappers.cmake import _ValueWrapper

import six
from six.moves import range


# --------------------------------------------------------------------------------------
# Constants

_TEST_TRUTHY_VALUES = [
    "true",
    "True",
    "TRUE",
    "on",
    "On",
    "ON",
    "yes",
    "Yes",
    "YES",
    "y",
    "Y",
    "1",
    "2",
    1,
    2,
    True,
]

_TEST_FALSEY_VALUES = [
    "",
    "false",
    "False",
    "FALSE",
    "off",
    "Off",
    "OFF",
    "no",
    "No",
    "NO",
    "n",
    "N",
    "ignore",
    "Ignore",
    "IGNORE",
    "notfound",
    "NotFound",
    "NOTFOUND",
    "VARIABLE-NOTFOUND",
    "0",
    0,
    False,
]


# --------------------------------------------------------------------------------------
# Helpers


class Test_ValueWrapper(unittest.TestCase):
    """
    """

    def test_value(self):
        wrapper = _ValueWrapper(1)
        self.assertEqual(wrapper.value, 1)

    def test_equality(self):
        self.assertEqual(_ValueWrapper(1), _ValueWrapper(1))

        self.assertNotEqual(_ValueWrapper(None), _ValueWrapper(""))

    def test_str(self):
        self.assertEqual(six.text_type(_ValueWrapper(1)), "1")
        self.assertEqual(six.text_type(_ValueWrapper(True)), "True")
        self.assertEqual(six.text_type(_ValueWrapper(42.0)), "42.0")


class Test_BoolWrapper(unittest.TestCase):
    """
    """

    def test_truthy_value(self):
        for value in _TEST_TRUTHY_VALUES:
            wrapper = _BoolWrapper(value)
            self.assertEqual(wrapper.value, True)

    def test_falsey_value(self):
        for value in _TEST_FALSEY_VALUES:
            wrapper = _BoolWrapper(value)
            self.assertEqual(wrapper.value, False)

    def test_invalid_value(self):
        with self.assertRaises(ValueError):
            _BoolWrapper(dict())
            _BoolWrapper(list())
            _BoolWrapper(set())
            _BoolWrapper(tuple())
            _BoolWrapper(1.0)
            _BoolWrapper(-42.0)
            _BoolWrapper(lambda x: x)


class Test_ListWrapper(unittest.TestCase):
    """
    """

    def test_list_value(self):
        wrapper = _ListWrapper([0, 1, 2, 3])
        self.assertEqual(wrapper.value, [0, 1, 2, 3])

    def test_invalid_value(self):
        with self.assertRaises(ValueError):
            _ListWrapper(dict())
            _ListWrapper(set())
            _ListWrapper(tuple())
            _ListWrapper(1)
            _ListWrapper(1.0)
            _ListWrapper("0;1;2;3")
            _ListWrapper(lambda x: x)


# --------------------------------------------------------------------------------------
# Public API


class TestCMakeValueType(unittest.TestCase):
    """
    """

    def test_expected_members(self):
        expected_members = [
            CMakeValueType.BOOL,
            CMakeValueType.FILEPATH,
            CMakeValueType.PATH,
            CMakeValueType.STRING,
            CMakeValueType.INTERNAL,
        ]

        six.assertCountEqual(self, CMakeValueType.__members__, expected_members)

    def test_equality(self):
        self.assertEqual(CMakeValueType.BOOL, CMakeValueType.BOOL)

        self.assertNotEqual(CMakeValueType.STRING, "STRING")
        self.assertNotEqual(CMakeValueType.FILEPATH, CMakeValueType.PATH)

    def test_hashable(self):
        set(CMakeValueType.__members__)

    def test_from_name(self):
        name_to_member = {member.name: member for member in CMakeValueType.__members__}

        for name, member in name_to_member.items():
            self.assertEqual(CMakeValueType.from_name(name), member)


class TestCMakeCacheEntry(unittest.TestCase):
    """
    """

    def test_valid_name(self):
        CMakeCacheEntry("NAME", "Foo")

    def test_invalid_name_type_raises(self):
        with self.assertRaises(ValueError):
            CMakeCacheEntry(None, "VALUE")
            CMakeCacheEntry(1, "VALUE")

    def test_empty_name_raises(self):
        with self.assertRaises(ValueError):
            CMakeCacheEntry("", "VALUE")

    def test_list_value_validation(self):
        entry = CMakeCacheEntry("NAME", [1, 2, 3])

        self.assertIsInstance(entry._value_wrapper, _ListWrapper)
        self.assertEqual(entry.value, [1, 2, 3])

        self.assertEqual(six.text_type(entry), "NAME:STRING=1;2;3")

    def test_bool_value_validation(self):
        for value in _TEST_TRUTHY_VALUES:
            entry = CMakeCacheEntry("NAME", value, value_type=CMakeValueType.BOOL)

            self.assertIsInstance(entry._value_wrapper, _BoolWrapper)
            self.assertEqual(entry.value, True)
            self.assertEqual(entry.value_type, CMakeValueType.BOOL)

        for value in _TEST_FALSEY_VALUES:
            entry = CMakeCacheEntry("NAME", value, value_type=CMakeValueType.BOOL)

            self.assertIsInstance(entry._value_wrapper, _BoolWrapper)
            self.assertEqual(entry.value, False)
            self.assertEqual(entry.value_type, CMakeValueType.BOOL)

    def test_string_value(self):
        entry = CMakeCacheEntry("NAME", "Bar")
        self.assertEqual(entry.value, "Bar")

    def test_numeric_value(self):
        entry = CMakeCacheEntry("NAME", 42)
        self.assertEqual(entry.value, 42)
        self.assertEqual(six.text_type(entry), "NAME=42")

        entry = CMakeCacheEntry("NAME", 2.718)
        self.assertEqual(entry.value, 2.718)
        self.assertEqual(six.text_type(entry), "NAME=2.718")

    def test_value_type_name_lookup(self):
        CMakeCacheEntry("NAME", "VALUE", value_type="BOOL")
        CMakeCacheEntry("NAME", "VALUE", value_type="FILEPATH")
        CMakeCacheEntry("NAME", "VALUE", value_type="PATH")
        CMakeCacheEntry("NAME", "VALUE", value_type="STRING")
        CMakeCacheEntry("NAME", "VALUE", value_type="INTERNAL")

    def test_invalid_value_type_name_raises(self):
        with self.assertRaises(ValueError):
            CMakeCacheEntry("NAME", "VALUE", "INVALID_TYPE")

    def test_equality(self):
        e1 = CMakeCacheEntry("A", None)
        e2 = CMakeCacheEntry("B", None)
        e3 = CMakeCacheEntry("B", "Foo")
        e4 = CMakeCacheEntry("B", "Foo", value_type=CMakeValueType.STRING)

        self.assertEqual(e1, e1)
        self.assertEqual(e1, CMakeCacheEntry("A", None))

        self.assertNotEqual(e1, e2)
        self.assertNotEqual(e2, e3)
        self.assertNotEqual(e3, e4)

    def test_str(self):
        self.assertEqual(
            six.text_type(CMakeCacheEntry("NAME", "VALUE")), "NAME=VALUE",
        )

        self.assertEqual(
            six.text_type(CMakeCacheEntry("NAME", "VALUE", "STRING")),
            "NAME:STRING=VALUE",
        )

        self.assertEqual(
            six.text_type(CMakeCacheEntry("NAME", True, "BOOL")), "NAME:BOOL=TRUE",
        )

        self.assertEqual(
            six.text_type(CMakeCacheEntry("NAME", [0, 1, 2])), "NAME:STRING=0;1;2",
        )

    def test_name_property(self):
        entry = CMakeCacheEntry("NAME", "VALUE", "INTERNAL")

        self.assertEqual(entry.name, "NAME")

    def test_value_property(self):
        entry = CMakeCacheEntry("NAME", "VALUE", "INTERNAL")

        self.assertEqual(entry.value, "VALUE")

    def test_value_type_property(self):
        entry = CMakeCacheEntry("NAME", "VALUE", "INTERNAL")

        self.assertEqual(entry.value_type, CMakeValueType.INTERNAL)


class TestCMakeCache(unittest.TestCase):
    """
    """

    def test_iter(self):
        cache = CMakeCache()

        for i in range(0, 10):
            cache.set("VAR{}".format(i), i, value_type="STRING")

        values = [entry.value for entry in cache]
        self.assertEqual(values, list(range(0, 10)))

    def test_len(self):
        cache = CMakeCache()

        self.assertEqual(len(cache), 0)

        cache.set("NAME", "VALUE")
        self.assertEqual(len(cache), 1)

        cache.set("FOO", 0)
        cache.set("BAR", 1)
        cache.set("BAZ", 2)
        self.assertEqual(len(cache), 4)

    def test_contains(self):
        cache = CMakeCache()

        cache.set("FOO", 0)
        cache.set("BAR", 1)
        cache.set("BAZ", 2)

        self.assertIn("FOO", cache)
        self.assertIn("BAR", cache)
        self.assertIn("BAZ", cache)

        self.assertNotIn("QUX", cache)

    def test_getitem(self):
        cache = CMakeCache()

        cache.set("FOO", 0)
        cache.set("BAR", 1)
        cache.set("BAZ", 2)

        self.assertEqual(cache["FOO"], CMakeCacheEntry("FOO", 0))

        with self.assertRaises(KeyError):
            cache["QUX"]

    def test_setitem(self):
        cache = CMakeCache()

        cache["FOO"] = 0
        self.assertEqual(cache.get("FOO"), CMakeCacheEntry("FOO", 0))

    def test_delitem(self):
        cache = CMakeCache()

        cache.set("FOO", 0)
        self.assertIn("FOO", cache)

        del cache["FOO"]
        self.assertNotIn("FOO", cache)

    def test_add(self):
        cache = CMakeCache()
        cache.set("FOO", 0)
        cache.set("BAR", 1)
        cache.set("BAZ", 2)

        other_cache = CMakeCache()
        other_cache.set("BAZ", 3)
        other_cache.set("QUX", 4)

        combined_cache = cache + other_cache
        six.assertCountEqual(
            self,
            combined_cache.entries,
            [
                CMakeCacheEntry("FOO", 0),
                CMakeCacheEntry("BAR", 1),
                CMakeCacheEntry("BAZ", 3),
                CMakeCacheEntry("QUX", 4),
            ],
        )

    def test_iadd(self):
        cache = CMakeCache()
        cache.set("FOO", 0)
        cache.set("BAR", 1)
        cache.set("BAZ", 2)

        other_cache = CMakeCache()
        other_cache.set("BAZ", 3)
        other_cache.set("QUX", 4)

        cache += other_cache
        six.assertCountEqual(
            self,
            cache.entries,
            [
                CMakeCacheEntry("FOO", 0),
                CMakeCacheEntry("BAR", 1),
                CMakeCacheEntry("BAZ", 3),
                CMakeCacheEntry("QUX", 4),
            ],
        )

    def test_entries_property(self):
        cache = CMakeCache()

        cache.set("FOO", 0)
        cache.set("BAR", 1)
        cache.set("BAZ", 2)

        six.assertCountEqual(
            self,
            cache.entries,
            [
                CMakeCacheEntry("FOO", 0),
                CMakeCacheEntry("BAR", 1),
                CMakeCacheEntry("BAZ", 2),
            ],
        )

    def test_args_property(self):
        cache = CMakeCache()

        cache.set("FOO", False)
        cache.set("BAR", "Foo")
        cache.set("BAZ", 42)
        cache.set("QUX", ["A", "B", "C"])

        self.assertEqual(
            cache.args,
            ["-DFOO:BOOL=FALSE", "-DBAR=Foo", "-DBAZ=42", "-DQUX:STRING=A;B;C"],
        )

    def test_get(self):
        cache = CMakeCache()
        cache.set("FOO", 0)
        cache.set("BAR", 1)
        cache.set("BAZ", 2)

        self.assertEqual(cache.get("FOO"), CMakeCacheEntry("FOO", 0))
        self.assertIsNone(cache.get("QUX"))

    def test_set(self):
        cache = CMakeCache()

        cache.set("FOO", "VALUE", value_type=CMakeValueType.STRING)
        cache.set("BAR", False, value_type=CMakeValueType.BOOL)
        cache.set("BAZ", [0, 1, 3])

        six.assertCountEqual(
            self,
            cache.entries,
            [
                CMakeCacheEntry("FOO", "VALUE", value_type=CMakeValueType.STRING),
                CMakeCacheEntry("BAR", False, value_type=CMakeValueType.BOOL),
                CMakeCacheEntry("BAZ", [0, 1, 3]),
            ],
        )

    def test_unset(self):
        cache = CMakeCache()

        cache.set("FOO", 0)
        self.assertIn("FOO", cache)

        cache.unset("FOO")
        self.assertNotIn("FOO", cache)

        with self.assertRaises(KeyError):
            cache.unset("FOO")

    def test_clear(self):
        cache = CMakeCache()

        cache.set("FOO", 0)
        cache.set("BAR", 1)
        cache.set("BAZ", 2)
        self.assertEqual(len(cache), 3)

        cache.clear()
        self.assertEqual(len(cache), 0)


class TestCMakeWrapper(unittest.TestCase):
    """
    """

    pass
