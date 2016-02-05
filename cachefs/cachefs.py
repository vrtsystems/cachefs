#!/usr/bin/python
# -*- coding: utf-8 -*-
# Cached file-system utility library
# (C) 2016 VRT Systems
#
# vim: set ts=4 sts=4 et tw=78 sw=4 si:

"""
cachefs: a cached filesystem abstraction library.

The purpose of this library is to provide a simple cache buffer for file system
operations.  Sometimes in a process you might need to know whether a file
changed, or what its permissions are, or its size, and you might need to know
in multiple places.  These different pieces of code may be completely oblivious
to each-other, and so rather than re-using the same result, you call `os.stat`
twice.

The concept here is to provide a way to cache filesystem metadata, for
situations where you know the files themselves won't change that frequently,
but you know you'll be needing to refer back to this information a lot.
"""

import time
import os
import weakref

from .node import Node
from pyat.base import TaskScheduler
from pyat.sync import SynchronousTaskScheduler

class CacheFs(object):
    '''
    A cached filesystem instance.  This holds strong references to nodes that
    are being frequently accessed by the end user.
    '''

    def __init__(self, cache_expiry, stat_expiry, scheduler=None):
        # node cache expiry
        self._cache_expiry = float(cache_expiry)

        # stat() expiry duration
        self._stat_expiry = float(stat_expiry)

        # Active nodes.
        self._nodes = {}

        # Scheduler instance.
        if scheduler is None:
            scheduler = SynchronousTaskScheduler()
        elif not isinstance(scheduler, TaskScheduler):
            raise TypeError('%r is not a TaskScheduler instance' % scheduler)
        self._scheduler = scheduler
        self._purge_task = None

    @property
    def _required_time(self):
        return time.time() - self._stat_expiry

    @property
    def _min_atime(self):
        return min([node._atime for node in self._nodes.values()])

    def _purge(self):
        '''
        Purge the cache of old entries.
        '''
        all_nodes = list(self._nodes.values())
        expired = list(filter(lambda n : n.atime_since > self._cache_expiry,
            all_nodes))
        for n in expired:
            try:
                del self._nodes[n.abs_path]
            except KeyError:  # pragma: no cover
                # Could happen in multi-threadded case, but harmless since
                # we're deleting anyway.
                pass
        if bool(self._nodes):
            self._purge_task = weakref.ref(self._scheduler.schedule(
                    self._min_atime + self._cache_expiry,
                    self._purge))
            self._scheduler.poll()
        else:
            self._purge_task = None

    def __getitem__(self, key):
        '''
        Return the filesystem node that corresponds to the named path.
        '''
        self._scheduler.poll()
        abs_path = os.path.abspath(key)
        try:
            node = self._nodes[abs_path]
        except KeyError:
            # No existing node, ensure it exists
            if not os.path.lexists(abs_path):
                # Path does not exist.
                raise KeyError(key)
            node = Node(self, abs_path)
            self._nodes[abs_path] = node
            if (self._purge_task is None) or (self._purge_task() is None):
                self._purge_task = weakref.ref(self._scheduler.schedule(
                        self._min_atime + self._cache_expiry,
                        self._purge))

        node._update_atime()
        return node

    def find(self, *args, **kwargs):
        '''
        Attempt to find nodes that match the given predicate.  The depth
        parameters control the minimum and maximum path depth (with depth
        itself overriding both).

        Each node is passed to the function called predicate which returns
        True or False.  If it returns True, find yields that node.
        '''
        for directory in args:
            for found in self[directory].find(**kwargs):
                yield found
