=======
History
=======

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
