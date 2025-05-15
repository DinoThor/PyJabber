from sqlalchemy import Table


class Model:
    Credentials: Table = None
    Roster: Table = None
    Pubsub: Table = None
    PubsubSubscribers: Table = None
    PubsubItems: Table = None
    PendingSubs: Table = None

    @staticmethod
    def setup(credentials, roster, pubsub, pubsub_subscribers, pubsub_items, pending_subs):
        Model.Credentials = credentials
        Model.Roster = roster
        Model.Pubsub = pubsub
        Model.PubsubSubscribers = pubsub_subscribers
        Model.PubsubItems = pubsub_items
        Model.PendingSubs = pending_subs
