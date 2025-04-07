class JID:
    def __init__(self, jid: str = None, user: str = None, domain: str = None, resource: str = None):
        if jid and (user or domain or resource):
            raise ValueError('You cannot pass user/domain/resource if a full jid is specified')

        if jid:
            try:
                self._user, domain = jid.split('@')
                try:
                    self._domain, self._resource = domain.split('/')
                except ValueError:
                    self._domain = domain
                    self._resource = None
            except ValueError:
                raise ValueError('Malformed JID')

        elif user and domain:
            self._user = user
            self._domain = domain
            self._resource = resource

        else:
            raise ValueError('Missing user and/or domain')

    @property
    def resource(self) -> str:
        return self._resource

    @resource.setter
    def resource(self, resource: str) -> None:
        self._resource = resource

    @property
    def domain(self) -> str:
        return self._domain

    @domain.setter
    def domain(self, domain: str):
        self._domain = domain

    @property
    def user(self) -> str:
        return self._user

    @user.setter
    def user(self, user: str):
        self._user = user

    def bare(self) -> str:
        return f'{self._user}@{self._domain}'

    def __str__(self):
        if self._resource:
            return f'{self._user}@{self._domain}/{self._resource}'
        return f'{self._user}@{self._domain}'

    def __eq__(self, other):
        if isinstance(other, JID):
            return self.user == other.user and self.domain == other.domain and self.resource == other.resource
        return False
