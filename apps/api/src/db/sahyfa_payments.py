from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import BigInteger, Column, ForeignKey, Index, JSON, Text, UniqueConstraint
from sqlmodel import Field, SQLModel


class SahyfaPaymentTransaction(SQLModel, table=True):
    __tablename__ = "sahyfa_payment_transaction"
    __table_args__ = (
        UniqueConstraint("provider", "authority", name="uq_sahyfa_payment_provider_authority"),
        Index("ix_sahyfa_payment_user_status", "user_id", "status"),
        Index("ix_sahyfa_payment_org_created", "org_id", "created_at"),
    )

    id: Optional[int] = Field(default=None, primary_key=True)
    org_id: int = Field(sa_column=Column(BigInteger, ForeignKey("organization.id", ondelete="CASCADE")))
    user_id: int = Field(sa_column=Column(BigInteger, ForeignKey("user.id", ondelete="CASCADE")))
    provider: str = Field(index=True)
    authority: str = Field(index=True)
    amount: int
    currency: str = "IRR"
    status: str = Field(default="pending", index=True)
    reference_id: Optional[str] = None
    description: str = ""
    callback_url: str = ""
    provider_data: Optional[dict] = Field(default=None, sa_column=Column(JSON))
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    verified_at: Optional[datetime] = None
