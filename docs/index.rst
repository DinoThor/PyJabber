PyJabber
########

PyJabber is an :ref:`MIT licensed <license>` XMPP server for Python 3.8+,

PyJabber is built upon three core principles:

**Low number of dependencies**
    PyJabber strikes to use a minimal number of external packages, using the
    included in the vanilla Python distro, Use well-established packages that
    have extensive documented and an active user community.

**Decoupled plugins architecture**
    XMPP's modular architecture relies on **XEPs (XMPP Extension Protocols)**,
    which extend its functionality in a flexible and decoupled way.
    Each XEP defines a specific feature, enabling interoperability and evolution
    without affecting the core protocol.

    Following this structure, PyJabber organized the plugins the same way, making
    easy to expand the functionality of the server without affecting any other part
    of the library. This encourages developers to collaborate with the project

**Asyncio based**
    "PyJabber employs the single-threaded asynchronous paradigm to maximize performance
    in I/O operations and handle large volumes of simultaneous connections. Additionally,
    its coroutine-based execution allows seamless integration with other programs to create
    powerful network services."


Quick start
-----------
Starting the server from code is as straightforward as:

.. code-block:: python

    from pyjabber import Server

    my_server = Server()
    asyncio.run(my_server.start())

PyJabber is also intended to be launched with his parameterizable CLI

.. code::

    $ pyjabber --help

.. code::

    Usage: pyjabber [OPTIONS]

        Options:
          --host TEXT                Host name  [default: localhost]
          --client_port INTEGER      Server-to-client port  [default: 5222]
          --server_port INTEGER      Server-to-server port  [default: 5269]
          --server_out_port INTEGER  Server-to-server port (Out coming connection)
                                     [default: 5269]
          --family [ipv4|ipv6]       (ipv4 / ipv6)  [default: ipv4]
          --timeout INTEGER          Timeout for connection  [default: 60]
          --database_path TEXT       Path for database file  [default: Current workdir]
          --database_purge           Restore database file to default state (empty)
          -v, --verbose              Show verbose debug level: -v level 1, -vv level
                                     2, -vvv level 3, -vvvv level 4
          --log_path TEXT            Path to log dumpfile
          -D, --debug                Enables debug mode in Asyncio
          --help                     Show this message and exit.

Documentation Index
-------------------

.. toctree::
    :maxdepth: 2

    installation
    licence
    architecture
    api/index

Additional Info
---------------
.. toctree::
    :hidden:

    license

* :ref:`license`


PyJabber Credits
---------------

**Main Author:**
    - Aarón Raya López (`Mail <xmpp:louiz@louiz.org?message>`_ | `Webpage <https://dinothor.github.io/>`_),

**Contributors:**
    - Manel Soler Sanz (`Mail <mailto:masosan9@upvnet.upv.es>`_ | `Webpage <https://sosanzma.github.io/>`_)
