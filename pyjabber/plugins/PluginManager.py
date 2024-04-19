from plugins.roster import Roster

class PluginManager():
    def __init__(self) -> None:
        
        self._plugins = {
            'jabber:iq:roster'      : Roster,
            
        }