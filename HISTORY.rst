=======
History
=======

0.1.9.post1 (2024-12-18)
-----------------------
* Update the README + HISTORY

0.1.9 (2024-12-17)
------------------
* Added Uvloop for unix-like os (improved loop event, compared to default asyncio loop)
* Fixed Windows bug with Ctrl+C and not being able to stop the server.
* Changed the async treatment of the server. Now the function start() returns a coroutine, and must be launched from ``asyncio.run()`` or similar

0.1.8 (2024-12-03)
------------------
* Fix previous release

0.1.7 (2024-12-03)
------------------

* Added Pubsub XEP (Service discovery, create node, delete node, publish, subscribe and retrieve subs)
* Added Service Discovery XEP
* Added Dataforms XEP
* Added --database_purge flag to reset database (erase any register)
* Refact singleton scheme
* Refact XEP scheme (migration to singleton)
* Create shared variables via contextvars
* Different refacts to the code

0.1.6 (2024-07-15)
------------------
* Updated depenencies version


0.1.5 (2024-08-12)
------------------
* Fixed minor bugs


0.1.4 (2024-07-15)
------------------
* Fixed minor bugs

0.1.3 (2024-07-12)
------------------
* Fixed bugs related to TLS (STARTTLS). Now, the constructor/CLI has a new boolean argument (*enable_tls1_3*). By default, the server will now accept up to TLSv1.2 to avoid some incompatibility found with legacy XMPP clients.
* Finished presence subscription for local bound (presence client within the same server)
* S2S available now (Creating and receiving connection from remote XMPP servers)
* Now it's possible to pass custom certificate via the constructor/CLI argument (path to the file). It will asume the names as {*name*}_cert.pem and {*name*}_key.pem
* Embedded script to create certificate bound with the hostname of the machine (*hostname*.local).
* Added unit test to the project (Thanks to @sosanzma)

0.1.2 (2024-05-31)
------------------

* Fixed minor bugs

0.1.1 (2024-05-30)
------------------

* First release on PyPI.
