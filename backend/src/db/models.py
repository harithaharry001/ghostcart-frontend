"""
SQLAlchemy ORM Models for GhostCart

Defines database models matching the schema in init_db.py.
AP2 Compliance: Models support complete mandate chain storage and job persistence.
"""
from datetime import datetime
from sqlalchemy import Column, String, Integer, Boolean, DateTime, ForeignKey, Text, CheckConstraint
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship

Base = declarative_base()


class MandateModel(Base):
    """
    ORM model for mandates table.

    Stores Intent, Cart, and Payment mandates with complete AP2 metadata.
    """
    __tablename__ = "mandates"

    id = Column(String, primary_key=True)
    mandate_type = Column(String, nullable=False)
    user_id = Column(String, nullable=False, index=True)
    transaction_id = Column(String, index=True)
    mandate_data = Column(Text, nullable=False)  # JSON blob
    signer_identity = Column(String, nullable=False)
    signature = Column(String, nullable=False)
    signature_metadata = Column(Text, nullable=False)  # JSON blob
    validation_status = Column(String, nullable=False)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        CheckConstraint("mandate_type IN ('intent', 'cart', 'payment')", name="mandate_type_check"),
        CheckConstraint("validation_status IN ('valid', 'invalid', 'unsigned')", name="validation_status_check"),
    )


class MonitoringJobModel(Base):
    """
    ORM model for monitoring_jobs table.

    Stores HNP autonomous monitoring job metadata with APScheduler integration.
    """
    __tablename__ = "monitoring_jobs"

    job_id = Column(String, primary_key=True)
    intent_mandate_id = Column(String, ForeignKey("mandates.id"), nullable=False)
    user_id = Column(String, nullable=False, index=True)
    product_query = Column(String, nullable=False)
    constraints = Column(Text, nullable=False)  # JSON blob
    schedule_interval_minutes = Column(Integer, nullable=False, default=5)
    active = Column(Boolean, nullable=False, default=True, index=True)
    last_check_at = Column(DateTime)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    expires_at = Column(DateTime, nullable=False, index=True)


class TransactionModel(Base):
    """
    ORM model for transactions table.

    Stores transaction results with links to complete mandate chain.
    """
    __tablename__ = "transactions"

    transaction_id = Column(String, primary_key=True)
    intent_mandate_id = Column(String, ForeignKey("mandates.id"))  # Nullable for HP context-only
    cart_mandate_id = Column(String, ForeignKey("mandates.id"), nullable=False)
    payment_mandate_id = Column(String, ForeignKey("mandates.id"), nullable=False)
    user_id = Column(String, nullable=False, index=True)
    status = Column(String, nullable=False, index=True)
    authorization_code = Column(String)
    decline_reason = Column(String)
    decline_code = Column(String)
    amount_cents = Column(Integer, nullable=False)
    currency = Column(String, nullable=False, default="USD")
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow, index=True)

    __table_args__ = (
        CheckConstraint("status IN ('authorized', 'declined', 'expired', 'failed')", name="status_check"),
    )


class SessionModel(Base):
    """
    ORM model for sessions table.

    Stores user session data for conversation continuity.
    """
    __tablename__ = "sessions"

    session_id = Column(String, primary_key=True)
    user_id = Column(String, nullable=False, index=True)
    current_flow_type = Column(String)
    context_data = Column(Text)  # JSON blob
    last_activity_at = Column(DateTime, nullable=False, default=datetime.utcnow, index=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    __table_args__ = (
        CheckConstraint("current_flow_type IN ('hp', 'hnp', 'none') OR current_flow_type IS NULL",
                       name="flow_type_check"),
    )
