from attrs import define
from xml.etree.ElementTree import Element

@define(frozen=True, slots=True)
class MailboxWrapper:
    """
    Represents a new published message on a topic.
    """

    payload: Element


@define(frozen=True, slots=True)
class PubSubSubscriptionWrapper:
    """
    Represents an update on the subscription state for a client.
    """

    payload: Element

