============
Quick Start
============


Launch server via CLI
---------------------

After PyJabber has been installed as explained in the :doc:`/installation`, you'll be able to launch a server instance 
directly from any terminal with just typing

.. code-block:: console

    $ pyjabber

.. code-block:: console

    {DATE} | INFO     | pyjabber.server:run_server:64 - Starting server...
    {DATE} | INFO     | pyjabber.server:run_server:95 - Client domain => localhost
    {DATE} | INFO     | pyjabber.server:run_server:96 - Server is listening clients on [('127.0.0.1', 5222), ('X.X.X.X', 5222)]
    {DATE} | INFO     | pyjabber.server:run_server:113 - Server is listening servers on [('0.0.0.0', 5269)]
    {DATE} | INFO     | pyjabber.server:run_server:114 - Server started...
    {DATE} | INFO     | pyjabber.webpage.adminPage:admin_instance:27 - Serving admin webpage on http://localhost:9090

This will start an instance with the default parameters, and ready to accept connections via the configured ports

You can also edit the parameters with the options and flags available

.. code-block:: console

  $ pyjabber --help


.. code-block:: console

  Options:
    --host TEXT                Host name  [default: localhost]
    --client_port INTEGER      Server-to-client port  [default: 5222]
    --server_port INTEGER      Server-to-server port  [default: 5269]
    --server_out_port INTEGER  Server-to-server port (Outcoming connection)
                              [default: 5269]
    --family [ipv4|ipv6]       (ipv4 / ipv6)  [default: ipv4]
    --tls1_3                   Enables TLSv1_3
    --timeout INTEGER          Timeout for connection  [default: 60]
    --log_level [INFO|DEBUG]   Log level alert  [default: INFO]
    --log_path TEXT            Path to log dumpfile
    -D, --debug                Enables debug mode in Asyncio
    --help                     Show this message and exit.

For example, to deploy a server that bounds with the host "example.com", and display the debug logger in the STDOUT:

.. code-block:: console

  $ pyjabber --host example.com --log_level DEBUG

Launch server via Python script
-------------------------------

Another way of deploy the server is to create a Server object instance

.. code-block:: python

  from pyjabber import Server

  my_server = Server()

and start to listening for new connections

.. code-block:: python

  my_server.start()

The Server object admits the same configuration that in the CLI 

.. code-block:: console

  Server class

  :param host: Host for the clients connections (localhost by default)
  :param client_port: Port for client connections (5222 by default)
  :param server_port: Port for server-to-server connections (5269 by default)
  :param family: Type of AddressFamily (IPv4 or IPv6)
  :param connection_timeout: Max time without any response from a client. After that, the server will terminate the connection
  :param enable_tls1_3: Boolean. Enables the use of TLSv1.3 in the STARTTLS process
  :parm cert_path: Path to custom domain certs. By default, the server generates its own certificates for hostname

.. code-block:: python

  my_server = Server (
        host='localhost',
        client_port=5222,
        server_port=5269,
        server_out_port=5269,
        family=socket.AF_INET,
        connection_timeout=60,
        enable_tls1_3=False,
        cert_path=None
  ):





