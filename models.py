from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .database import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    full_name: Mapped[str] = mapped_column(String(120))
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    phone: Mapped[str | None] = mapped_column(String(30), nullable=True)
    aadhaar_number: Mapped[str | None] = mapped_column(String(12), nullable=True, unique=True)
    upi_id: Mapped[str | None] = mapped_column(String(120), nullable=True)
    bank_account_number: Mapped[str | None] = mapped_column(String(40), nullable=True)
    bank_ifsc: Mapped[str | None] = mapped_column(String(20), nullable=True)
    permanent_address: Mapped[str | None] = mapped_column(Text, nullable=True)
    residential_address: Mapped[str | None] = mapped_column(Text, nullable=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    role: Mapped[str] = mapped_column(String(30), default="customer")
    preferred_language: Mapped[str] = mapped_column(String(10), default="en")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    provider_profile: Mapped["Provider | None"] = relationship(back_populates="user", uselist=False)


class Cooperative(Base):
    __tablename__ = "cooperatives"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(180))
    registration_number: Mapped[str] = mapped_column(String(80), unique=True)
    district: Mapped[str] = mapped_column(String(100))
    verified: Mapped[bool] = mapped_column(Boolean, default=False)


class Provider(Base):
    __tablename__ = "providers"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), unique=True)
    cooperative_id: Mapped[int | None] = mapped_column(ForeignKey("cooperatives.id"), nullable=True)
    verification_status: Mapped[str] = mapped_column(String(30), default="pending")
    certification_details: Mapped[str | None] = mapped_column(Text, nullable=True)
    latitude: Mapped[float] = mapped_column(Float)
    longitude: Mapped[float] = mapped_column(Float)
    service_radius_km: Mapped[float] = mapped_column(Float, default=15)
    available: Mapped[bool] = mapped_column(Boolean, default=True)
    insurance_policy_number: Mapped[str | None] = mapped_column(String(100), nullable=True)

    user: Mapped[User] = relationship(back_populates="provider_profile")
    skills: Mapped[list["Skill"]] = relationship(back_populates="provider", cascade="all, delete-orphan")


class Skill(Base):
    __tablename__ = "skills"

    id: Mapped[int] = mapped_column(primary_key=True)
    provider_id: Mapped[int] = mapped_column(ForeignKey("providers.id"))
    name: Mapped[str] = mapped_column(String(80), index=True)
    certification: Mapped[str | None] = mapped_column(String(160), nullable=True)
    years_experience: Mapped[int] = mapped_column(Integer, default=0)

    provider: Mapped[Provider] = relationship(back_populates="skills")


class Service(Base):
    __tablename__ = "services"

    id: Mapped[int] = mapped_column(primary_key=True)
    provider_id: Mapped[int] = mapped_column(ForeignKey("providers.id"))
    title: Mapped[str] = mapped_column(String(160))
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    category: Mapped[str] = mapped_column(String(80), index=True)
    hourly_rate: Mapped[float] = mapped_column(Float)
    active: Mapped[bool] = mapped_column(Boolean, default=True)


class Booking(Base):
    __tablename__ = "bookings"

    id: Mapped[int] = mapped_column(primary_key=True)
    customer_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    provider_id: Mapped[int] = mapped_column(ForeignKey("providers.id"))
    service_id: Mapped[int] = mapped_column(ForeignKey("services.id"))
    scheduled_for: Mapped[datetime] = mapped_column(DateTime)
    address: Mapped[str] = mapped_column(String(300))
    latitude: Mapped[float] = mapped_column(Float)
    longitude: Mapped[float] = mapped_column(Float)
    duration_hours: Mapped[float] = mapped_column(Float, default=1)
    status: Mapped[str] = mapped_column(String(30), default="requested")
    is_emergency: Mapped[bool] = mapped_column(Boolean, default=False)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    total_amount: Mapped[float] = mapped_column(Float, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class Payment(Base):
    __tablename__ = "payments"

    id: Mapped[int] = mapped_column(primary_key=True)
    booking_id: Mapped[int] = mapped_column(ForeignKey("bookings.id"), unique=True)
    amount: Mapped[float] = mapped_column(Float)
    status: Mapped[str] = mapped_column(String(30), default="pending")
    provider_reference: Mapped[str | None] = mapped_column(String(120), nullable=True)
    paid_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


class Review(Base):
    __tablename__ = "reviews"

    id: Mapped[int] = mapped_column(primary_key=True)
    booking_id: Mapped[int] = mapped_column(ForeignKey("bookings.id"), unique=True)
    customer_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    provider_id: Mapped[int] = mapped_column(ForeignKey("providers.id"))
    rating: Mapped[int] = mapped_column(Integer)
    comment: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class WelfareRecord(Base):
    __tablename__ = "welfare_records"

    id: Mapped[int] = mapped_column(primary_key=True)
    provider_id: Mapped[int] = mapped_column(ForeignKey("providers.id"))
    scheme_name: Mapped[str] = mapped_column(String(160))
    status: Mapped[str] = mapped_column(String(30), default="active")
    valid_until: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
