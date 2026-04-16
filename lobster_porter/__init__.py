"""
lobster_porter — 龍蝦搬運工
============================

A Python package for batch-moving, organising, and classifying documents
(Markdown, PDF, Word, etc.) in a documentation repository.

Highlights
----------
- Bulk transport of files between directories with configurable strategies
- Pluggable architecture: drop in a new plugin to add custom behaviour
- Clear extension points marked with ``# TODO`` where you should add logic

Public API
----------
The most common entry points exported from this package:

``Porter``
    The main worker class. Instantiate, configure, and call ``.run()``.

``BaseStrategy``
    Abstract base class for transport/classification strategies.

``BasePlugin``
    Abstract base class for plugins.

Example
-------
>>> from lobster_porter import Porter
>>> porter = Porter(src="./inbox", dest="./organised")
>>> porter.run()

Version
-------
.. code-block:: text

    0.1.0  — initial skeleton

"""

__version__ = "0.1.0"
__author__ = "dicwong630-jpg"
__all__ = ["Porter"]

from lobster_porter.core import Porter  # noqa: F401
