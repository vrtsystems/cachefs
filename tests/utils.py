#!/usr/bin/python
# -*- coding: utf-8 -*-
# Cached file-system utility library
# (C) 2016 VRT Systems
#
# vim: set ts=4 sts=4 et tw=78 sw=4:

import errno
import os
import tempfile

class SimpleTempdir(object):
    '''
    Generate a simple directory structure with:
    - a subdirectory named 'subdir',
    - two files:
        - 'a' (top-level)
        - 'b' (inside 'subdir')
    - if supported, four links:
        - 'to_subdir' (top-level, pointing to 'subdir')
        - 'top' (in 'subdir', pointing to absolute path of top-level)
        - 'a' (inside 'subdir', pointing to '../a')
        - 'to_a' (top-level, pointing to 'subdir/a')
        - 'broken' (top-level, pointing to 'nowhere')
    '''
    def __init__(self):
        self.tempdir = None
        self.file_a = None
        self.dir_subdir = None
        self.file_b = None

        self.to_unlink = []
        self.to_rmdir = []
        self.all_files = set()

        if hasattr(os, 'symlink'):
            self.link_to_subdir = None
            self.link_a = None
            self.link_to_a = None
            self.link_top = None
            self.link_broken = None

    def __del__(self):
        self.delete()

    def make(self):
        self.tempdir = tempfile.mkdtemp()
        self.file_a = os.path.join(self.tempdir, 'a')
        self.dir_subdir = os.path.join(self.tempdir, 'subdir')
        self.file_b = os.path.join(self.dir_subdir, 'b')

        self.all_files.update(set([
            self.tempdir, self.file_a, self.dir_subdir, self.file_b
        ]))

        self.to_unlink.extend([self.file_a, self.file_b])
        self.to_rmdir.extend([self.dir_subdir, self.tempdir])

        os.mkdir(self.dir_subdir)
        open(self.file_a, 'w').write('file a')
        open(self.file_b, 'w').write('file b')

        if hasattr(os, 'symlink'):
            self.link_to_subdir = os.path.join(self.tempdir, 'to_subdir')
            self.link_a = os.path.join(self.dir_subdir, 'a')
            self.link_to_a = os.path.join(self.tempdir, 'to_a')
            self.link_top = os.path.join(self.dir_subdir, 'top')
            self.link_broken = os.path.join(self.tempdir, 'broken')
            self.all_files.update(set([
                self.link_to_subdir, self.link_a, self.link_to_a,
                self.link_top, self.link_broken
            ]))

            os.symlink('subdir', self.link_to_subdir)
            os.symlink(self.tempdir, self.link_top)
            os.symlink('../a', self.link_a)
            os.symlink('subdir/a', self.link_to_a)
            os.symlink('nowhere', self.link_broken)
            self.to_unlink.extend([self.link_to_subdir, self.link_a,
                    self.link_to_a, self.link_top, self.link_broken])

    def delete(self):
        for name in self.to_unlink:
            try:
                os.unlink(name)
            except OSError as e:
                if e.errno != errno.ENOENT:
                    raise

        for name in self.to_rmdir:
            try:
                os.rmdir(name)
            except OSError as e:
                if e.errno != errno.ENOENT:
                    raise


class TempDirTestCase(object):
    temp_dir = None

    @classmethod
    def setup_class(cls):
        cls.temp_dir = SimpleTempdir()
        cls.temp_dir.make()

    @classmethod
    def teardown_class(cls):
        cls.temp_dir.delete()


def compare_walk(walk1, walk2):
    # Lengths should match
    assert len(walk1) == len(walk2)

    # First and last visited directory should match.
    assert walk1[0][0] == walk2[0][0], \
            'First visited directory does not match'
    assert walk1[-1][0] == walk2[-1][0], \
            'Last visited directory does not match'

    # Collate by directory, since order may not exactly match.
    to_dict = lambda w : dict([(base, (dirs, files)) \
            for (base, dirs, files) in w])
    walk1 = to_dict(walk1)
    walk2 = to_dict(walk2)

    # List of directories should match
    assert set(walk1.keys()) == set(walk2.keys()), \
            'Visited directories did not match'

    for base in walk1.keys():
        (dirs1, files1) = walk1[base]
        (dirs2, files2) = walk2[base]

        assert set(dirs1) == set(dirs2), 'Directories do not match'
        assert set(files1) == set(files2), 'Files do not match'
