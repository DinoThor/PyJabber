==================
SPADE Architecture
==================

Even if this project offers an open-source server for any XMPP application, the main goal in its creation is the leverage of the
functionality in the multi-agent system SPADE.
With the use of this library, an agent can be able to deploy it's own XMPP server, avoiding the dependency of third parties and even
the need of a internet connection (usefully in isolated IoT environments).
This leads to a scenario where servers are deployed dynamically, on machines without any IP or host previously known. A correct deployment
goes through a configuration, verification, certification and release in the public domain. Trying to avoid any need of interaction with the
user in the deployment of the server, we've opted to use the following architecture

Local Bound
-----------
Let's use a fictional environment compound of 4 agents, all allocated in the same local network.
A random agent takes the action, and deploy a server reachable for the other 3 agent via the local network. This new server will
be serving to the clients in the domain of his own hostname.
This means, that the agents should adopt the JID format of ``{unique-name}@hostname``.

For example, a list of agents connected to a server deployed in the ``testing-desktop`` machine takes the following format:

::

        agent1@testing-desktop
        agent2@testing-desktop
        agent3@testing-desktop
