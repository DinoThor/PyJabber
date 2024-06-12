========
PyJabber
========


.. image:: https://img.shields.io/pypi/v/pyjabber.svg
        :target: https://pypi.org/project/pyjabber/

.. image:: https://shields.io/badge/python-3.8%20%7C%203.9%20%7C%203.10%20-blue
        :alt: Python 3.8 | 3.9 | 3.10

.. image:: https://img.shields.io/github/actions/workflow/status/dinothor/pyjabber/python-app.yml
        :target: https://github.com/DinoThor/PyJabber/actions
        :alt: CI status

.. image:: https://readthedocs.org/projects/pyjabber/badge/?version=latest
        :target: https://pyjabber.readthedocs.io/en/latest/?version=latest
        :alt: Documentation Status

.. image:: https://img.shields.io/pypi/dm/pyjabber
        :target: https://www.pepy.tech/projects/pyjabber
        :alt: Monthly downloads

.. image:: https://img.shields.io/pepy/dt/pyjabber
        :target: https://www.pepy.tech/projects/pyjabber
        :alt: Total downloads



|
| PyJabber is a server for Jabber/XMPP entirely written in Python, with minimal reliance on external libraries.
| It strives to provide a simple, lightweight, and comprehensible codebase, featuring a modular structure that
        facilitates extension through the implementation of necessary XEPs for specific use cases.
| While initially designed to fulfill the requirements of the multi-agent system `SPADE <https://github.com/javipalanca/spade>`_, it can be easily customized to suit any other purpose.
|

* Free software: MIT license
* Documentation: https://pyjabber.readthedocs.io.

Installation
------------
.. code-block::

        pip install pyjabber

Quick start
-----------
.. code-block:: python

        from pyjabber import Server

        my_server = Server()
        my_server.start()

or

.. code-block:: python

        python -m pyjabber --help

.. code-block::

        Usage: python -m pyjabber [OPTIONS]

        Options:
          --host TEXT               Host name  [default: localhost]
          --client_port INTEGER     Server-to-client port  [default: 5222]
          --server_port INTEGER     Server-to-server port  [default: 5269]
          --family [ipv4|ipv6]      (ipv4 / ipv6)  [default: ipv4]
          --timeout INTEGER         Timeout for connection  [default: 60]
          --log_level [INFO|DEBUG]  Log level alert  [default: INFO]
          --log_path TEXT           Path to log dumpfile.
          -D, --debug               Enables debug mode in Asyncio.
          --help                    Show this message and exit.


Features
--------

.. list-table::
   :widths: 25 25 50
   :header-rows: 1

   * -
     - Status
     - Description
   * - TLS
     - Implemented
     - v1.2, with localhost certificate and CA included
   * - SASL
     - Implemented
     - PLAIN
   * - Roster
     - Implemented
     - CRUD avaliable
   * - Presence
     - Partialy implemented
     - Subscribe, Unsubscribed, Initial presence and Unavailable

Plugins
-------
.. list-table::
   :widths: 25 25 50
   :header-rows: 1

   * -
     - Status
     - Description
   * - `XEP-0077 <https://xmpp.org/extensions/xep-0077.html>`_
     - IMPLEMENTED
     -
   * - `XEP-0199 <https://xmpp.org/extensions/xep-0199.html>`_
     - IMPLEMENTED
     -
