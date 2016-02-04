#!/usr/bin/python
# -*- coding: utf-8 -*-
# Cached file-system utility library
# (C) 2016 VRT Systems
#
# vim: set ts=4 sts=4 et tw=78 sw=4:

import weakref
import time
import os
import threading

class _Node(object):
    '''
    This is a back-end caching object, which is referenced by the
    user-accessible Node object.
    '''

    # A listing of all possible nodes, by absolute path.
    _ALL_NODES = weakref.WeakValueDictionary()
    _ALL_NODES_LK = threading.Lock()

    @classmethod
    def get_node(cls, abs_path):
        with cls._ALL_NODES_LK:
            try:
                node = cls._ALL_NODES[abs_path]
            except KeyError:
                node = cls(abs_path)
        return node

    def __init__(self, abs_path):
        assert self._ALL_NODES_LK.locked(), \
                'Mutex not locked'
        assert abs_path not in self._ALL_NODES, \
                'Duplicate for %r' % abs_path

        # Multithreading lock
        self._lock = threading.Lock()

        # Full path of this node
        self.abs_path = abs_path

        # Base name for the path (lazy evaluation)
        self._base_name = None

        # Directory name for the path (lazy evaluation)
        self._dir_name = None

        # Last `stat` call
        self._last_stat = 0.0

        # Result of last lstat()
        self._stat = None

        # Modification time of directory when last listing was collected
        self._children_last = 0.0

        # Known children, by name
        self._children = set()

        # Make ourselves known.
        self._ALL_NODES[abs_path] = self

        # Link target name
        self._target = None

        # Target modification time
        self._target_last = 0.0

    @property
    def dir_name(self):
        if self._dir_name is None:
            self._dir_name = os.path.dirname(self.abs_path)
        return self._dir_name

    @property
    def base_name(self):
        if self._base_name is None:
            self._base_name = os.path.basename(self.abs_path)
        return self._base_name

    def _get_stat(self, since_time):
        if since_time > self._last_stat:
            # Refresh the statistics.
            self._stat = os.lstat(self.abs_path)
            self._last_stat = time.time()
        return self._stat

    def _get_children(self, since_time):
        if since_time > self._children_last:
            # Update the child listing.
            self._children = set(os.listdir(self.abs_path))
            self._children_last = time.time()
        return self._children

    def _get_target(self, since_time):
        if since_time > self._target_last:
            # Update the link target.
            self._target = os.readlink(self.abs_path)
            self._target_last = time.time()
        return self._target

    def get_stat(self, since_time):
        '''
        Retrieve the statistics, refreshing them if they're not newer than
        "since_time" (a Unix timestamp; from time.time()).
        '''
        with self._lock:
            return self._get_stat(since_time)

    def get_target(self, since_time):
        '''
        Retrieve the link target, refreshing it if it's not newer than
        "since_time" (a Unix timestamp; from time.time()).
        '''
        with self._lock:
            return self._get_target(since_time)

    def get_children(self, since_time):
        '''
        Retrieve the child listing for this node, refreshing if the modification
        time of this node is greater than what it was when the child list was
        last retrieved.
        '''
        with self._lock:
            return self._get_children(since_time)
