#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Test Suite for Unball utility classes and functions."""

__author__  = "Stephan Sokolow (deitarion/SSokolow)"
__license__ = "GNU GPL 2.0 or later"

import logging, sys
log = logging.getLogger(__name__)

if sys.version_info[0] == 2 and sys.version_info[1] < 7:  # pragma: no cover
    import unittest2 as unittest
    unittest  # Silence erroneous PyFlakes warning
else:                                                     # pragma: no cover
    import unittest

from unball.util import BinYes, which  # , NamedTemporaryFolder

class TestBinYes(unittest.TestCase):
    def test_callability(self):
        """Test that BinYes requires no extra instantiation"""
        for method in ('fileno', 'read'):
            try:
                getattr(BinYes, method)()
            except TypeError:  # pragma: no cover
                self.fail(("BinYes.%s() must be callable without first "
                "having to instantiate BinYes.") % method)

    def test_fileno(self):
        """Test the fileno() method of util.BinYes"""
        self.assertTrue(hasattr(BinYes, 'fileno'),
                "BinYes must have a fileno() method for compatibility.")

        self.assertIsNone(BinYes.fileno(),
                "fileno() must return None if there's no OS-level file"
                "handle associated with it as in BinYes.")

    def test_read(self):
        """Test the return value of BinYes.read()

        @todo: Decide on a policy for str vs. unicode
        """
        self.assertRegexpMatches(BinYes.read(), '(y\n)+',
            "read() must return a sequence of one or more 'y\\n' substrings")
        self.assertRegexpMatches(BinYes.read(10), '(y\n)+',
            "read(i) must return a sequence of one or more 'y\\n' substrings")
        self.assertLessEqual(len(BinYes.read(10)), 10,
            "read(10) must return no more than 10 characters.")

        for i in xrange(0, 100):
            self.assertRegexpMatches(BinYes.read(), '(y\n)+',
                "read() must support being called any number of times")

        #TODO: Move what follows into test_read_odd() once it doesn't fail.
        req_len = 5
        self.assertNotEqual(req_len % 2, 0,
            "This test is broken and requires a request length that would "
            "split a 'y\\n' substring.")

        test_return = BinYes.read(req_len)
        self.assertLessEqual(len(test_return), req_len,
            "read() may return a string shorter than request but not longer.")

    @unittest.expectedFailure
    def test_read_odd(self):
        """Test that odd read() sizes don't break the 'y\\n' pairs."""
        self.assertLessEqual(len(BinYes.read(1)), 1,
            "read(1) must return no more than 1 character.")
        self.assertEqual(len(BinYes.read(1)), 1,
            "read(1) may not return zero characters because it could "
            "break fragile subprocesses.")

        self.fail("BinYes needs to be redesigned to ensure that read(1) can be"
            " supported without risking a subprocess receiving '\\n' as its"
            " first line of input and assuming it to mean 'use default'"
            " because a previous user of BinYes read an odd number of"
            " characters.")

        #TODO: Test that sequential read(1) calls preserve the repeating
        #      'y\n' subsequence.

class TestNamedTemporaryFolder(unittest.TestCase):
    """Stuff to test in NamedTemporaryFolder:
        - Unicode vs. str for all string inputs
        - suffix, prefix, and dir individually set and unset for for __init__
        - Context manager use in general
        - len(parent_listdir_before) ==
          len(parent_listdir_during) -1 ==
          len(parent_listdir_after)
        - Return value of __enter__
        - __exit__ should pass exceptions through
        - OSError should be raised on failure to delete the tempdir
        - No error should be raised if the temporary directory doesn't exist at
          the expected name on __exit__
        - If the temporary directory is renamed to preserve it, __exit__ must
          not delete it anyway.
        - The context manager must create the folder on __enter__, not
          __init__, so one instance can be reused.
        - An attempt to treat a single instance as reentrant should fail loudly
          rather than leaving un-collected folders

        @todo: Look into how to test a context manager for GC-safety.
    """

#TODO: Test TempTarget and which() fully and properly
def test_which():
    """Placeholder integration test for which()

    @todo: Test which() fully, properly, and portably
    """
    assert which('sh') == which('sh', '/bin') == '/bin/sh'
