========
PyJabber
========


.. image:: https://img.shields.io/pypi/v/pyjabber.svg
        :target: https://pypi.python.org/pypi/pyjabber

.. image:: https://img.shields.io/travis/dinothor/pyjabber.svg
        :target: https://travis-ci.com/dinothor/pyjabber

.. image:: https://readthedocs.org/projects/pyjabber/badge/?version=latest
        :target: https://pyjabber.readthedocs.io/en/latest/?version=latest
        :alt: Documentation Status


|         
| PyJabber is a server for Jabber/XMPP entirely written in Python, with minimal reliance on external libraries. 
| It strives to provide a simple, lightweight, and comprehensible codebase, featuring a modular structure that 
        facilitates extension through the implementation of necessary XEPs for specific use cases. 
| While initially designed to fulfill the requirements of the multi-agent system `SPADE <https://github.com/javipalanca/spade>`_, it can be easily customized to suit any other purpose.
|

* Free software: MIT license
* Documentation: https://pyjabber.readthedocs.io.

Quick start
-----------
.. code-block:: python
        
        from pyjabber import Server

        my_server = Server()
        my_server.start()

.. code-block:: python

        class Server(
            host                : str = "localhost",
            client_port         : int = 5222,
            server_port         : int = 5223,
            connection_timeout  : int = 60
        )

A formated logger can be added, in order to retrive the messages from the INFO, DEBUG and ERROR levels

.. code-block:: python
    
    2024-05-03 11:45:51.229 | INFO     | pyjabber.server:run_server:52 - Starting server...
    2024-05-03 11:45:51.231 | INFO     | pyjabber.server:run_server:73 - Server is listening clients on ('127.0.0.1', 5222)
    2024-05-03 11:45:51.231 | INFO     | pyjabber.server:run_server:75 - Server started...




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
     - v1.2, with localhost certificate included
   * - SASL
     - Implemented
     - PLAIN
   * - Roster
     - Implemented
     - CRUD avaliable
   * - Presence
     - Not implemented
     - Working on it

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