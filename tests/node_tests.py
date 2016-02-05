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
    HAS_LINKS = getattr(os, 'symlink')

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
        if not self.HAS_LINKS:
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

    def test_node_base_name(self):
        cache = cachefs.CacheFs(cache_expiry=2.0, stat_expiry=1.0)

        # Get a reference to one of the files.
        node = cache[self.temp_dir.file_a]
        assert node.base_name == os.path.basename(self.temp_dir.file_a), \
                'Base name does not match'

    def test_node_dir_name(self):
        cache = cachefs.CacheFs(cache_expiry=2.0, stat_expiry=1.0)

        # Get a reference to one of the files.
        node = cache[self.temp_dir.file_a]
        assert node.dir_name == os.path.dirname(self.temp_dir.file_a), \
                'Directory name does not match'

    def test_node_join(self):
        cache = cachefs.CacheFs(cache_expiry=2.0, stat_expiry=1.0)

        # Get a reference to one of the files.
        node = cache[self.temp_dir.tempdir]
        assert node.join('abcd', 'efgh') == \
                os.path.join(self.temp_dir.tempdir, 'abcd', 'efgh'), \
                'Path does not match'

    def test_node_join_node(self):
        cache = cachefs.CacheFs(cache_expiry=2.0, stat_expiry=1.0)

        # Get a reference to one of the files.
        node_dir = cache[self.temp_dir.tempdir]
        node_a = cache[self.temp_dir.file_a]
        assert node_dir.join_node(node_a.base_name) is node_a

    def test_node_type(self):
        cache = cachefs.CacheFs(cache_expiry=2.0, stat_expiry=1.0)

        node = cache[self.temp_dir.tempdir]
        assert node.is_dir, 'Apparently not a directory'
        assert not node.is_file, 'Apparently a file'
        if self.HAS_LINKS:
            assert not node.is_link, 'Apparently a link'

        node = cache[self.temp_dir.file_a]
        assert not node.is_dir, 'Apparently a directory'
        assert node.is_file, 'Apparently not a file'
        if self.HAS_LINKS:
            assert not node.is_link, 'Apparently a link'

        if self.HAS_LINKS:
            node = cache[self.temp_dir.link_a]
            assert not node.is_dir, 'Apparently a directory'
            assert not node.is_file, 'Apparently a file'
            assert node.is_link, 'Apparently not a link'

    def test_symlink_target(self):
        if not self.HAS_LINKS:
            raise SkipTest

        cache = cachefs.CacheFs(cache_expiry=2.0, stat_expiry=1.0)
        assert cache[self.temp_dir.link_to_subdir].target == 'subdir'
        assert cache[self.temp_dir.link_top].target == self.temp_dir.tempdir
        assert cache[self.temp_dir.link_a].target == '../a'
        assert cache[self.temp_dir.link_to_a].target == 'subdir/a'
        assert cache[self.temp_dir.link_broken].target == 'nowhere'

    def test_symlink_abs_target(self):
        if not self.HAS_LINKS:
            raise SkipTest

        cache = cachefs.CacheFs(cache_expiry=2.0, stat_expiry=1.0)
        assert cache[self.temp_dir.link_to_subdir].abs_target \
                == os.path.join(self.temp_dir.tempdir, 'subdir')
        assert cache[self.temp_dir.link_top].abs_target == self.temp_dir.tempdir
        assert cache[self.temp_dir.link_a].abs_target \
                == os.path.join(self.temp_dir.tempdir, 'a')
        assert cache[self.temp_dir.link_to_a].abs_target \
                == os.path.join(self.temp_dir.tempdir, 'subdir', 'a')
        assert cache[self.temp_dir.link_broken].abs_target \
                == os.path.join(self.temp_dir.tempdir, 'nowhere')

    def test_symlink_abs_final_target(self):
        if not self.HAS_LINKS:
            raise SkipTest

        cache = cachefs.CacheFs(cache_expiry=2.0, stat_expiry=1.0)
        assert cache[self.temp_dir.link_to_subdir].abs_final_target \
                == os.path.join(self.temp_dir.tempdir, 'subdir')
        assert cache[self.temp_dir.link_top].abs_final_target \
                == self.temp_dir.tempdir
        assert cache[self.temp_dir.link_a].abs_final_target \
                == os.path.join(self.temp_dir.tempdir, 'a')
        assert cache[self.temp_dir.link_to_a].abs_final_target \
                == os.path.join(self.temp_dir.tempdir, 'a')
        assert cache[self.temp_dir.link_broken].abs_final_target \
                == os.path.join(self.temp_dir.tempdir, 'nowhere')

    def test_symlink_target_node(self):
        if not self.HAS_LINKS:
            raise SkipTest

        cache = cachefs.CacheFs(cache_expiry=2.0, stat_expiry=1.0)
        assert cache[self.temp_dir.link_to_subdir].target_node \
                is cache[self.temp_dir.dir_subdir]
        assert cache[self.temp_dir.link_top].target_node \
                is cache[self.temp_dir.tempdir]
        assert cache[self.temp_dir.link_a].target_node \
                is cache[self.temp_dir.file_a]
        assert cache[self.temp_dir.link_to_a].target_node \
                is cache[self.temp_dir.link_a]
        # This should raise a KeyError
        try:
            cache[self.temp_dir.link_broken].target_node
            assert False, 'Target apparently exists'
        except KeyError:
            pass

    def test_symlink_final_target_node(self):
        if not self.HAS_LINKS:
            raise SkipTest

        cache = cachefs.CacheFs(cache_expiry=2.0, stat_expiry=1.0)
        assert cache[self.temp_dir.link_to_subdir].final_target_node \
                is cache[self.temp_dir.dir_subdir]
        assert cache[self.temp_dir.link_top].final_target_node \
                is cache[self.temp_dir.tempdir]
        assert cache[self.temp_dir.link_a].final_target_node \
                is cache[self.temp_dir.file_a]
        assert cache[self.temp_dir.link_to_a].final_target_node \
                is cache[self.temp_dir.file_a]
        # This should raise a KeyError
        try:
            cache[self.temp_dir.link_broken].final_target_node
            assert False, 'Target apparently exists'
        except KeyError:
            pass

    def test_node_getitem(self):
        cache = cachefs.CacheFs(cache_expiry=2.0, stat_expiry=1.0)
        node_dir = cache[self.temp_dir.tempdir]
        node_file = cache[self.temp_dir.file_a]
        child = node_dir[node_file.base_name]
        assert node_file is child

    def test_node_iter(self):
        expected = set(['a', 'subdir'])
        if self.HAS_LINKS:
            expected.update(set(['to_subdir', 'to_a', 'broken']))

        cache = cachefs.CacheFs(cache_expiry=2.0, stat_expiry=1.0)
        node = cache[self.temp_dir.tempdir]
        children = set(node)
        assert children == expected

    def test_node_iter(self):
        if self.HAS_LINKS:
            expected = 5
        else:
            expected = 2

        cache = cachefs.CacheFs(cache_expiry=2.0, stat_expiry=1.0)
        node = cache[self.temp_dir.tempdir]
        num_children = len(node)
        assert num_children == expected

    def test_node_find_all_breadth_first(self):
        cache = cachefs.CacheFs(cache_expiry=2.0, stat_expiry=1.0)
        nodes = list(cache[self.temp_dir.tempdir].find(depth_first=False))
        file_names = [n.abs_path for n in nodes]

        # Check all files are present
        assert set(file_names) == self.temp_dir.all_files

        # Check the depths of each file
        base = len(self.temp_dir.tempdir.split(os.path.sep))
        depths = [len(name.split(os.path.sep)) for name in file_names]
        if self.HAS_LINKS:
            # Expected order:
            depths_expected = [
                    base,       # top-level directory
                    base + 1,   # .../subdir
                    base + 1,   # .../a
                    base + 1,   # .../to_a
                    base + 1,   # .../to_subdir
                    base + 1,   # .../broken
                    base + 2,   # .../subdir/a
                    base + 2,   # .../subdir/b
                    base + 2,   # .../subdir/top
            ]
        else:
            # Expected order:
            depths_expected = [
                    base,       # top-level directory
                    base + 1,   # .../a
                    base + 1,   # .../subdir
                    base + 2,   # .../subdir/b
            ]
        assert depths == depths_expected

    def test_node_find_all_depth_first(self):
        cache = cachefs.CacheFs(cache_expiry=2.0, stat_expiry=1.0)
        nodes = list(cache[self.temp_dir.tempdir].find(depth_first=True))
        file_names = [n.abs_path for n in nodes]

        # Check all files are present
        assert set(file_names) == self.temp_dir.all_files

        # Check the depths of each file
        base = len(self.temp_dir.tempdir.split(os.path.sep))
        depths = [len(name.split(os.path.sep)) for name in file_names]
        if self.HAS_LINKS:
            # Expected order:
            depths_expected = [
                    base + 2,   # .../subdir/a
                    base + 2,   # .../subdir/b
                    base + 2,   # .../subdir/top
                    base + 1,   # .../subdir
                    base + 1,   # .../a
                    base + 1,   # .../to_a
                    base + 1,   # .../to_subdir
                    base + 1,   # .../broken
                    base,       # top-level directory
            ]
        else:
            # Expected order:
            depths_expected = [
                    base + 2,   # .../subdir/b
                    base + 1,   # .../a
                    base + 1,   # .../subdir
                    base,       # top-level directory
            ]
        assert depths == depths_expected

    def test_node_find_specific_depth(self):
        cache = cachefs.CacheFs(cache_expiry=2.0, stat_expiry=1.0)
        node = cache[self.temp_dir.tempdir]
        file_names = set([n.abs_path for n in node.find(depth=1)])
        # We should just see the children of the top-level directory.
        assert file_names == set([c.abs_path for c in node.values()])

    def test_node_find_min_depth(self):
        cache = cachefs.CacheFs(cache_expiry=2.0, stat_expiry=1.0)
        node = cache[self.temp_dir.tempdir]
        file_names = set([n.abs_path for n in node.find(min_depth=1)])
        # We should just see everything except the top-level directory.
        assert file_names == \
                (self.temp_dir.all_files - set([self.temp_dir.tempdir]))

    def test_node_find_max_depth(self):
        cache = cachefs.CacheFs(cache_expiry=2.0, stat_expiry=1.0)
        node = cache[self.temp_dir.tempdir]
        file_names = set([n.abs_path for n in node.find(max_depth=1)])
        # We should see the top-level directory and its children
        assert file_names == (set([self.temp_dir.tempdir]) | \
                set([c.abs_path for c in node.values()]))

    def test_node_find_depth_range(self):
        cache = cachefs.CacheFs(cache_expiry=2.0, stat_expiry=1.0)
        node = cache[self.temp_dir.tempdir]
        file_names = set([n.abs_path for n in node.find(
            min_depth=1, max_depth=2)])
        # We should just see everything except the top-level directory.
        assert file_names == \
                (self.temp_dir.all_files - set([self.temp_dir.tempdir]))
