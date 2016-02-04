#!/usr/bin/python
# -*- coding: utf-8 -*-
# Cached file-system utility library
# (C) 2016 VRT Systems
#
# vim: set ts=4 sts=4 et tw=78 sw=4:

from nose.plugins.skip import SkipTest
from cachefs import intnode
import os
import weakref
import tempfile
import stat
import time

from .utils import TempDirTestCase

class TestIntNode(TempDirTestCase):
    def test_is_singleton(self):
        n1 = intnode._Node.get_node(self.temp_dir.tempdir)
        n2 = intnode._Node.get_node(self.temp_dir.tempdir)

        assert n1 is n2, 'Different instances returned'

    def test_is_weak(self):
        cwd = os.getcwd()
        n = intnode._Node.get_node(self.temp_dir.tempdir)
        nr = weakref.ref(n)

        del n
        assert nr() is None, 'Node still exists'

    def test_names(self):
        cwd = os.getcwd()
        n = intnode._Node.get_node(self.temp_dir.tempdir)
        assert n.base_name == os.path.basename(n.abs_path), \
                'Base name doesn\'t match'
        assert n.dir_name == os.path.dirname(n.abs_path), \
                'Directory name doesn\'t match'

    def test_symlink(self):
        if not hasattr(os, 'symlink'):
            # Host system doesn't support symbolic links.
            raise SkipTest()

        symlink_node = intnode._Node.get_node(self.temp_dir.link_a)
        now = time.time()

        # Ensure we're looking at the symlink
        assert stat.S_ISLNK(symlink_node.get_stat(now).st_mode), \
                'Not a symbolic link'

        # Ensure it points where we created it.
        target = symlink_node.get_target(now)
        assert target == '../a', 'Link points someplace else'

    def test_stat_cache(self):
        now = time.time()

        # Get a reference to one of the files.
        node = intnode._Node.get_node(self.temp_dir.file_a)

        # Get its size.
        size_1 = node.get_stat(now).st_size

        # Make a change to that file.
        open(self.temp_dir.file_a,'a').write(' -- some data')

        # Get its size.  It should not have changed.
        size_2 = node.get_stat(now).st_size
        assert size_1 == size_2, 'Cached data refreshed.'

        # Get it again, pretending it's 5 minutes later.
        size_3 = node.get_stat(now + 300.0).st_size

        assert size_1 < size_3, 'Cached data not refreshed.'

    def test_child_cache(self):
        # Generate a child directory filename
        child_file = os.path.join(self.temp_dir.tempdir, 'testfile')
        try:
            now = time.time()

            # Get a reference to the temp directory.
            node = intnode._Node.get_node(self.temp_dir.tempdir)

            # Get its child list.
            children_1 = node.get_children(now)

            # Create a child.
            open(child_file,'w').write('new file')

            # Get the children again.  It should not have changed.
            children_2 = node.get_children(now)
            assert children_1 == children_2, 'Cached data refreshed.'

            # Get it again, pretending it's 5 minutes later.
            children_3 = node.get_children(now + 300.0)

            # There should be an extra file.
            assert (children_3 - children_1) == set(['testfile']), \
                    'Cached data not refreshed.'
        finally:
            os.unlink(child_file)
