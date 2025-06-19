.. raw:: html

    <h1 style="text-align: center">PyJabber</h1>

.. image:: https://raw.githubusercontent.com/DinoThor/PyJabber/refs/heads/master/logo.png
        :width: 300px
        :alt: Logo
        :align: center

.. image:: https://img.shields.io/pypi/v/pyjabber.svg
        :target: https://pypi.org/project/pyjabber/

.. image:: https://img.shields.io/badge/python-3.9%20%7C%203.10%20%7C%203.11%20%7C%203.12-blue
        :alt: Python 3.8 to 3.12

.. image:: https://img.shields.io/github/actions/workflow/status/dinothor/pyjabber/python-app.yml
        :target: https://github.com/DinoThor/PyJabber/actions
        :alt: Build Status

.. image:: https://coveralls.io/repos/github/DinoThor/PyJabber/badge.svg?branch=master
        :target: https://coveralls.io/github/DinoThor/PyJabber?branch=master
        :alt: Coverage Status

.. image:: https://tokei.rs/b1/github/dinothor/pyjabber
        :alt: Code lines counter

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

------------
Installation
------------
.. code-block::

        pip install pyjabber

-----------
Quick start
-----------

Python program
--------------

The process of starting the server returns a coroutine, leaving it to the user to set up the required environment. The simplest approach is to use the ``asyncio.run`` function.

.. code-block:: python

    from pyjabber import Server

    my_server = Server()
    asyncio.run(my_server.start())

This allows PyJabber to be treated as a regular task and integrated seamlessly into an asynchronous application.

.. code-block:: python

    import asyncio
    from pyjabber.server import Server

    async def counter():
      while True:
        await asyncio.sleep(1)
        print(f"Hello World")

    async def launch():
      my_server = Server()
      await asyncio.gather(my_server.start(), counter())

    asyncio.run(launch())

CLI
---
The CLI launcher provides access to all the configuration options available in the programmatic version (when launched from a Python script).


.. code-block:: python


        $ pyjabber --help


.. code-block::


       Usage: python -m pyjabber [OPTIONS]

        Options:
          --host TEXT                Host name  [default: localhost]
          --client_port INTEGER      Server-to-client port  [default: 5222]
          --server_port INTEGER      Server-to-server port  [default: 5269]
          --server_out_port INTEGER  Server-to-server port (Out coming connection)
                                     [default: 5269]
          --family [ipv4|ipv6]       (ipv4 / ipv6)  [default: ipv4]
          --timeout INTEGER          Timeout for connection  [default: 60]
          --database_path TEXT       Path for database file  [default: */pyjabber.db]
          --database_purge           Restore database file to default state (empty)
          --database_in_memory       Database in memory. The data will be erased after
                                     server shutdown
          --message_persistence      Keep the unsent messages in memory waiting for
                                     the receiver client to connect
          -v, --verbose              Show verbose debug level: -v INFO -vv DEBUG, -vvv
                                     level TRACE,
          --log_path TEXT            Path to log dumpfile
          -D, --debug                Enables debug mode in Asyncio
          --help                     Show this message and exit.


And to launch a default profile

.. code-block::


        $ pyjabber


.. code-block::

        2024-12-18 09:03:22.880 - INFO: Starting server...
        2024-12-18 09:03:22.881 - INFO: Client domain => localhost
        2024-12-18 09:03:22.881 - INFO: Server is listening clients on [('127.0.0.1', 5222), ('158.42.155.44', 5222)]
        2024-12-18 09:03:22.881 - INFO: Serving admin webpage on http://localhost:9090
        2024-12-18 09:03:22.881 - INFO: Server is listening servers on [('0.0.0.0', 5269)]
        2024-12-18 09:03:22.881 - INFO: Server started...

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
     - v1.3. Localhost certificate included
   * - SASL
     - Implemented
     - PLAIN, EXTERNAL (s2s)
   * - Roster
     - Implemented
     - CRUD avaliable
   * - Presence
     - Implemented (local bound)
     - Subscribe, Unsubscribed, Initial presence and Unavailable

Plugins
-------
.. list-table::
   :widths: 25 25 50
   :header-rows: 1

   * -
     - Status
     - Description
   * - `XEP-0004 <https://xmpp.org/extensions/xep-0004.html>`_
     - IMPLEMENTED
     - Dataforms
   * - `XEP-0030 <https://xmpp.org/extensions/xep-0030.html>`_
     - IMPLEMENTED
     - Service Discovery
   * - `XEP-0060 <https://xmpp.org/extensions/xep-0077.html>`_
     - IMPLEMENTED
     - Pubsub
   * - `XEP-0077 <https://xmpp.org/extensions/xep-0077.html>`_
     - IMPLEMENTED
     - In Band Registration
   * - `XEP-0199 <https://xmpp.org/extensions/xep-0199.html>`_
     - IMPLEMENTED
     - Ping
