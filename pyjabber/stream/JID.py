class JID:
    def __init__(self, jid: str = None, user: str = None, domain: str = None, resource: str = None):
        if jid:
            self._user = jid.split('/')[0]
            self._domain = jid.split('@')[-1].split('/')[0]
            self._resource = jid.split('@')[0]

        elif user and domain and resource:
            self._user = user
            self._domain = domain
            self._resource = resource

        else:
            """
            https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcQ4Rjd2fP4k__PEhyVfyEKDaoBDN_i03yGvJw&s
            """
            raise Exception

    @property
    def resource(self) -> str:
        return self._resource

    @property
    def domain(self) -> str:
        return self._domain

    @property
    def user(self) -> str:
        return self._user

    def bare(self) -> str:
        return f'{self._user}@{self._domain}'

    def __str__(self):
        if self._resource:
            return f'{self._user}@{self._domain}/{self._resource}'
        return f'{self._user}@{self._domain}'

