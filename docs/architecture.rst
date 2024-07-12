============
Architecture
============

.. image:: res/arch.png
  :alt: Alternative text

|
| A PyJabber Server is built by an asyncio loop, with an unique XMLProtocol object instanced and associated
    by each TCP connection made.
| An instance of Server will have an unique (Singleton) instance of a ConnectionManager object. This will keep an unique list of Peers
    connected to the server (and the server itself other servers), and will be visible (but no mutable) for each XMPPProtocol instance.


Client Stream
-------------
#. TCP connection:
    A client connects by host:5222. PyJabber will create an **XMLProtocol** instance for this new connection,
    bound it and store it in the **ConnectionManager** singleton (the tcp:port information along with the buffer object used to send data)
#. Stream Negotiation:
    Client and PyJabber will start an XML message flow in order to establish the session.
    This steep includes the process of securing the socket with SSL certificate (startTLS), authentication/registration of the
    client and its resource binding. This step will be managed by the **StreamHandler**.
#. Stanza Management:
    After the stream has been negotiated, a session will be started between
    server and client, and stanzas will be treated by the **StanzaHandler**. This stage is where the majority
    of the application will be, and stanzas of **IQ**, **PRESENCE** and **MESSAGE** are treated.
    The StanzaHandler object comes with all the plugins (XEPs) and features available, and it's his responsibility to treat any received
    message and his routing or request processing and response
