from sqlalchemy import Table, MetaData, Column, Integer, String

# global Credentials: Table = None
# global Roster: Table = None
# global Pubsub: Table = None
# global PubsubSubscribers: Table = None
# global PubsubItems: Table = None
# global PendingSubs: Table = None

class ModelTest:
    Credentials: Table = None
    Roster: Table = None
    Pubsub: Table = None
    PubsubSubscribers: Table = None
    PubsubItems: Table = None
    PendingSubs: Table = None

    mock_meta = MetaData()
    Credentials = Table(
        "credentials", mock_meta,
        Column("id", Integer, primary_key=True),
        Column("jid", String, nullable=False),
        Column("hash_pwd", String, nullable=False)
    )

    Roster = Table(
        "roster", mock_meta,
        Column("id", Integer, primary_key=True, autoincrement=True),
        Column("jid", String, nullable=False),
        Column("roster_item", String, nullable=False)
    )

    Pubsub = Table(
        "pubsub", mock_meta,
        Column("node", String, primary_key=True),
        Column("owner", String, nullable=False),
        Column("name", String),
        Column("type", String),
        Column("max_items", Integer)
    )

    PubsubSubscribers = Table(
        "pubsub_subscribers", mock_meta,
        Column("node", String, primary_key=True),
        Column("jid", String, primary_key=True),
        Column("subid", String, primary_key=True),
        Column("subscription", String, nullable=False),
        Column("affiliation", String, nullable=False)
    )

    PubsubItems = Table(
        "pubsub_items", mock_meta,
        Column("node", String, primary_key=True),
        Column("publisher", String, nullable=False),
        Column("item_id", String, primary_key=True),
        Column("payload", String, nullable=False)
    )

    PendingSubs = Table(
        "pending_subs", mock_meta,
        Column("jid", String, primary_key=True),
        Column("item", String, primary_key=True)
    )
