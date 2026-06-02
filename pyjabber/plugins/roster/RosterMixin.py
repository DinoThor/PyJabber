from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pyjabber.features.presence.PresenceFeature import Presence
    BaseClass = Presence
else:
    BaseClass = object

class RosterMixin(BaseClass):
    """
    This Mixin groups all the public methods used for another
    components for the server.
    """
    pass
