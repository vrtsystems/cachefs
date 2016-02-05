#!/usr/bin/python
# -*- coding: utf-8 -*-
# Cached file-system utility library
# (C) 2016 VRT Systems
#
# vim: set ts=4 sts=4 et tw=78 sw=4 si:

import time
import os
import errno
import collections
import stat
import weakref

from .intnode import _Node


class Node(collections.Mapping):
    '''
    A file-system node object.  This represents a file or directory within
    the filesystem.  It has a weak reference to the parent node and holds the
    metadata for that node.
    '''

    def __init__(self, cache, abs_path):
        self._cache = weakref.ref(cache)
        self._node = _Node.get_node(abs_path)
        self._atime = time.time()

    def _update_atime(self):
        self._atime = time.time()

    @property
    def atime(self):
        return self._atime

    @property
    def atime_since(self):
        return time.time() - self.atime

    # Python conveniences

    def __repr__(self):  # pragma: no cover
        # Not covered, because it's just for convenience
        return '%s(%r, %r)' % (
                self.__class__.__name__, self._cache(), self.abs_path)

    def __str__(self):  # pragma: no cover
        # Not covered, because it's just for convenience
        if self.is_file:
            file_type = 'file'
        elif self.is_dir:
            file_type = 'dir'
        elif self.is_link:
            file_type = 'link'
        else:
            file_type = 'other'

        return '%s{%r %s}' % (
                self.__class__.__name__, self.abs_path, file_type)

    def __bool__(self): # pragma: no cover
        '''
        Return True if the node exists.
        '''
        # Not covered, because it's just for convenience
        try:
            self.stat
            return True
        except OSError:
            return False

    # Node properties

    @property
    def abs_path(self):
        '''
        Return the node's full absolute path.
        '''
        return self._node.abs_path

    @property
    def dir_name(self):
        '''
        Return the full path of the node's parent directory.
        '''
        return self._node.dir_name

    @property
    def base_name(self):
        '''
        Return the full path of the node's parent.
        '''
        return self._node.base_name

    def join(self, *elements):
        '''
        Return a path below this node with *elements added.
        '''
        return os.path.join(self.abs_path, *elements)

    @property
    def stat(self):
        '''
        Return the result of os.stat() on this file.
        '''
        self._update_atime()
        return self._node.get_stat(self._cache()._required_time)

    @property
    def file_type(self):
        '''
        Returns the file type for the file.
        '''
        return stat.S_IFMT(self.stat.st_mode)

    @property
    def is_socket(self):
        '''
        Return true if the file is a socket.
        '''
        return self.file_type == stat.S_IFSOCK

    @property
    def is_link(self):
        '''
        Return true if the file is a symbolic link.
        '''
        return self.file_type == stat.S_IFLNK

    @property
    def is_file(self):
        '''
        Return true if the file is a regular file.
        '''
        return self.file_type == stat.S_IFREG

    @property
    def is_dir(self):
        '''
        Return true if the file is a directory.
        '''
        return self.file_type == stat.S_IFDIR

    @property
    def is_char(self):
        '''
        Return true if the file is a character device.
        '''
        return self.file_type == stat.S_IFCHR

    @property
    def is_fifo(self):
        '''
        Return true if the file is a FIFO.
        '''
        return self.file_type == stat.S_IFIFO

    # Handling of links.

    @property
    def target(self):
        '''
        Returns the name of the file the symlink points to.
        '''
        return self._node.get_target(self._cache()._required_time)

    @property
    def abs_target(self):
        '''
        Returns the absolute path for the target.
        '''
        return os.path.abspath(self.join(self.target))

    @property
    def abs_final_target(self):
        '''
        Returns the absolute path for the target, following all symlinks.
        '''
        return os.path.realpath(self.abs_path)

    @property
    def target_node(self):
        '''
        Return the filesystem node pointed to by this symlink.
        '''
        return self._cache()[self.abs_target]

    @property
    def final_target_node(self):
        '''
        Return the filesystem node pointed to by this symlink.
        '''
        return self._cache()[self.abs_final_target]

    # Mapping interface for directories.

    def __getitem__(self, key):
        '''
        Return the child filesystem node named 'key'.
        '''
        self._update_atime()
        abs_path = os.path.join(self.abs_path, key)
        return self._cache()[abs_path]

    def __iter__(self):
        '''
        Return an iterator for all the children in this directory.
        '''
        self._update_atime()
        return iter(self._node.get_children(\
                self._cache()._required_time).copy())

    def __len__(self):
        '''
        Return the number of child elements in the directory.
        '''
        self._update_atime()
        return len(self._node.get_children(\
                self._cache()._required_time))

    # Searching for child nodes.

    def _find(self, predicate, depth_predicate, depth, depth_first):
        if self.is_link:
            for found in self.final_target_node._find(
                    predicate, depth_predicate, depth, depth_first):
                yield found
            return

        child_depth = depth+1
        show_self = depth_predicate(depth)
        show_children = depth_predicate(child_depth)
        recurse = depth_predicate(depth, True)

        if not self.is_dir:
            if show_self and predicate(self):
                yield self
            return

        # Apply predicate to self if not depth first
        if (not depth_first) and show_self and predicate(self):
            yield self

        for child in self.values():
            # Apply predicate to child if not a directory
            if show_children and (not child.is_dir) and predicate(child):
                yield child

            # Recurse into child if a directory
            elif recurse and child.is_dir:
                for found in child._find(predicate, depth_predicate,
                        child_depth, depth_first):
                    yield found

        # Apply predicate to self if depth first
        if depth_first and show_self and predicate(self):
            yield self

    def find(self, predicate=None, depth=None, min_depth=None, max_depth=None,
            depth_first=False):
        '''
        Attempt to find nodes that match the given predicate.  The depth
        parameters control the minimum and maximum path depth (with depth
        itself overriding both).

        Each node is passed to the function called predicate which returns
        True or False.  If it returns True, find yields that node.
        '''
        if depth is not None:
            depth_predicate = lambda d, r=False : \
                    r or (d == depth)
        elif (min_depth is None) and (max_depth is None):
            depth_predicate = lambda d, r=False : True
        elif (min_depth is not None) and (max_depth is None):
            depth_predicate = lambda d, r=False : \
                    r or (d >= min_depth)
        elif (min_depth is None) and (max_depth is not None):
            depth_predicate = lambda d, r=False : \
                    r or (d <= max_depth)
        elif (min_depth is not None) and (max_depth is not None):
            depth_predicate = lambda d, r=False : \
                    r or ((d >= min_depth) and (d <= max_depth))

        if predicate is None:
            predicate = lambda n : True
        for found in self._find(predicate, depth_predicate, 0, depth_first):
            yield found

def _raise_oserror(err, path):
    raise OSError(err, os.strerror(err), path)
