#!/usr/bin/python
# -*- coding: utf-8 -*-
# Cached file-system utility library
# (C) 2016 VRT Systems
#
# vim: set ts=4 sts=4 et tw=78 sw=4:

import cachefs
from pyat.sync import SynchronousTaskScheduler
from .utils import TempDirTestCase, compare_walk
import weakref
import time
import os

class TestCacheFs(TempDirTestCase):
    def test_cachefs_scheduler_typeerror(self):
        try:
            cache = cachefs.CacheFs(cache_expiry=2.0, stat_expiry=1.0, \
                    scheduler='bogga')
            assert False, 'It accepted a string'
        except TypeError:
            pass

    def test_ref_held_by_cache(self):
        cache = cachefs.CacheFs(cache_expiry=2.0, stat_expiry=1.0)
        n = cache[self.temp_dir.tempdir]
        nr = weakref.ref(n)
        del n

        # Check that we get this same reference back
        assert cache[self.temp_dir.tempdir] is nr(), \
                'Got back a new reference'

    def test_does_not_exist(self):
        cache = cachefs.CacheFs(cache_expiry=2.0, stat_expiry=1.0)
        try:
            cache[os.path.join(self.temp_dir.tempdir, 'nonexistant')]
            assert False, 'We got a file that does not exist'
        except KeyError:
            pass

    def test_ref_purged_by_cache(self):
        scheduler = SynchronousTaskScheduler()
        cache = cachefs.CacheFs(cache_expiry=2.0, stat_expiry=1.0,
                scheduler=scheduler)
        n1 = cache[self.temp_dir.tempdir]
        n2 = cache[self.temp_dir.file_a]
        n1r = weakref.ref(n1)
        n2r = weakref.ref(n2)

        # Drop our hard references
        del n1, n2

        time.sleep(1.0)
        scheduler.poll()
        assert n1r() is not None, 'Lost from cache'
        assert n2r() is not None, 'Lost from cache'

        # Poke n2 to tweak its mtime.
        n2r()._update_atime()

        time.sleep(1.0)
        scheduler.poll()

        # Check that the reference n1 has gone, n2 is present
        assert n1r() is None, 'Still in cache'
        assert n2r() is not None, 'Lost from cache'

        time.sleep(1.0)
        scheduler.poll()

        # Check that the reference n2 has gone
        assert n2r() is None, 'Still in cache'
