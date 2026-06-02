import asyncio
from xml.etree.ElementTree import Element

from sqlalchemy import select

from pyjabber.db.database import DB
from pyjabber.db.model import Model
from pyjabber.plugins.xep_0060.wrappers import MailboxWrapper
from pyjabber.utils.Singleton import singleton


@singleton
class PubSubBroker:
    def __init__(self):
        self._mailbox_queue = asyncio.Queue()
        self._subscription_queue = asyncio.Queue()

        self._subscription_status = None

        # with DB.connection() as con:
        #     query = select(Model.Pubsub)
        #     res = con.execute(query)
        #     self._nodes = res.fetchall()
        #
        #     query = select(Model.PubsubSubscribers)
        #     res = await con.execute(query)
        #     self._subscribers = res.fetchall()

    async def start(self):
        mailbox_task = asyncio.create_task(self._mailbox_queue.get())
        subscription_task = asyncio.create_task(self._subscription_queue.get())

        pending = {mailbox_task, subscription_task}

        try:
            while True:
                done, pending = await asyncio.wait(
                    pending,
                    return_when=asyncio.FIRST_COMPLETED
                )

                for task in done:
                    msg = task.result()
                    if isinstance(msg, MailboxWrapper):


                        mailbox_task = asyncio.create_task(self._mailbox_queue.get())
                        pending.add(mailbox_task)
        except asyncio.CancelledError:
            pass


    async def _filter(self, stanza: Element):
        pass
