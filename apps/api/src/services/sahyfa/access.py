from datetime import datetime

from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from src.db.usergroup_user import UserGroupUser
from src.db.usergroups import UserGroup
from src.services.webhooks.dispatch import dispatch_webhooks


async def grant_verified_payment_access(
    session: AsyncSession,
    *,
    org_id: int,
    user_id: int,
    usergroup_uuid: str,
) -> bool:
    """Grant a paid user's access through the existing LearnHouse group model.

    Returns ``True`` only when a membership row was created. Replayed gateway
    callbacks are therefore harmless and do not emit duplicate access events.
    """
    group_result = await session.exec(
        select(UserGroup).where(UserGroup.org_id == org_id, UserGroup.usergroup_uuid == usergroup_uuid)
    )
    group = group_result.one_or_none()
    if group is None or group.id is None:
        raise LookupError("Payment access group was not found")

    member_result = await session.exec(
        select(UserGroupUser).where(
            UserGroupUser.org_id == org_id,
            UserGroupUser.usergroup_id == group.id,
            UserGroupUser.user_id == user_id,
        )
    )
    if member_result.one_or_none() is not None:
        return False

    now = str(datetime.now())
    session.add(
        UserGroupUser(
            usergroup_id=group.id,
            user_id=user_id,
            org_id=org_id,
            creation_date=now,
            update_date=now,
        )
    )
    await session.commit()
    await dispatch_webhooks(
        event_name="usergroup_users_added",
        org_id=org_id,
        data={"usergroup_id": group.id, "usergroup_uuid": usergroup_uuid, "user_ids": [user_id]},
    )
    return True
