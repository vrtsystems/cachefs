#!/usr/bin/python
# -*- coding: utf-8 -*-
# Cached file-system utility library
# (C) 2016 VRT Systems
#
# vim: set ts=4 sts=4 et tw=78 sw=4:

from nose.plugins.skip import SkipTest
import cachefs
import os
import weakref
import tempfile
import stat
import time

from .utils import TempDirTestCase, compare_walk

class TestNode(TempDirTestCase):
    def test_stat_cache(self):
        cache = cachefs.CacheFs(cache_expiry=2.0, stat_expiry=1.0)

        # Get a reference to one of the files.
        node = cache[self.temp_dir.file_a]

        # Get its size.
        size_1 = node.stat.st_size

        # Make a change to that file.
        open(self.temp_dir.file_a,'a').write(' -- some data')

        # Get its size.  It should not have changed.
        size_2 = node.stat.st_size
        assert size_1 == size_2, 'Cached data refreshed.'

        # Wait for expiry.
        time.sleep(1.5)

        # Get it again.
        size_3 = node.stat.st_size

        assert size_1 < size_3, 'Cached data not refreshed.'

    def test_find_all(self):
        cache = cachefs.CacheFs(cache_expiry=2.0, stat_expiry=1.0)
        found_names = set([found.abs_path for found in
                cache.find(self.temp_dir.tempdir)])

        assert found_names == self.temp_dir.all_files, 'A file was missed'

    def test_find_all_link(self):
        if not hasattr(os, 'symlink'):
            raise SkipTest
        cache = cachefs.CacheFs(cache_expiry=2.0, stat_expiry=1.0)
        found_names = set([found.abs_path for found in
                cache.find(self.temp_dir.link_top)])

        assert found_names == self.temp_dir.all_files, 'A file was missed'

    def test_find_file(self):
        cache = cachefs.CacheFs(cache_expiry=2.0, stat_expiry=1.0)
        found_names = set([found.abs_path for found in
                cache.find(self.temp_dir.file_a)])

        assert found_names == set([self.temp_dir.file_a]), \
                'Mismatch in expected list'
