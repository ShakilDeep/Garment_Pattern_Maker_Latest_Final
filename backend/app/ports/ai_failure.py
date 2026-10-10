"""Port error shared by every AI adapter: the provider failed (``unavailable``) or answered unreadably."""


class ProviderFailure(Exception):
    def __init__(self, provider: str, *, unavailable: bool):
        self.provider, self.unavailable = provider, unavailable
        super().__init__(f"{provider} {'unavailable' if unavailable else 'returned invalid output'}")
