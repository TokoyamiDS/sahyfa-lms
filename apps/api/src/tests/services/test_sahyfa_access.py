import pytest

from src.db.usergroup_user import UserGroupUser
from src.db.usergroups import UserGroup
from src.services.sahyfa.access import grant_verified_payment_access


class Result:
    def __init__(self, value):
        self.value = value

    def one_or_none(self):
        return self.value


class Session:
    def __init__(self, group, member=None):
        self.group = group
        self.member = member
        self.added = []
        self.commits = 0
        self.calls = 0

    async def exec(self, query):
        self.calls += 1
        return Result(self.group if self.calls == 1 else self.member)

    def add(self, value):
        self.added.append(value)

    async def commit(self):
        self.commits += 1


@pytest.mark.asyncio
async def test_grant_access_is_idempotent(monkeypatch):
    group = UserGroup(id=4, org_id=1, usergroup_uuid="paid-course", name="Paid", description="")
    session = Session(group, None)
    events = []

    async def capture_event(**kwargs):
        events.append(kwargs)

    monkeypatch.setattr("src.services.sahyfa.access.dispatch_webhooks", capture_event)

    created = await grant_verified_payment_access(session, org_id=1, user_id=8, usergroup_uuid="paid-course")

    assert created is True
    assert isinstance(session.added[0], UserGroupUser)
    assert session.commits == 1
    assert len(events) == 1
