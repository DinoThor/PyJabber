from sqlalchemy import Table, MetaData, Column, Integer, String


class Model:
    server_metadata = MetaData()

    Credentials = Table(
        "credentials", server_metadata,
        Column("id", Integer, primary_key=True),
        Column("jid", String, nullable=False),
        Column("hash_pwd", String, nullable=False)
    )

    Roster = Table(
        "roster", server_metadata,
        Column("id", Integer, primary_key=True, autoincrement=True),
        Column("jid", String, nullable=False),
        Column("roster_item", String, nullable=False)
    )

    Pubsub = Table(
        "pubsub", server_metadata,
        Column("node", String, primary_key=True),
        Column("owner", String, nullable=False),
        Column("name", String),
        Column("type", String),
        Column("max_items", Integer)
    )

    PubsubSubscribers = Table(
        "pubsub_subscribers", server_metadata,
        Column("node", String, primary_key=True),
        Column("jid", String, primary_key=True),
        Column("subid", String, primary_key=True),
        Column("subscription", String, nullable=False),
        Column("affiliation", String, nullable=False)
    )

    PubsubItems = Table(
        "pubsub_items", server_metadata,
        Column("node", String, primary_key=True),
        Column("publisher", String, nullable=False),
        Column("item_id", String, primary_key=True),
        Column("payload", String, nullable=False)
    )

    PendingSubs = Table(
        "pending_subs", server_metadata,
        Column("jid", String, primary_key=True),
        Column("item", String, primary_key=True)
    )
