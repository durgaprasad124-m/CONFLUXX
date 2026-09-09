from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field, model_validator


class UserCreate(BaseModel):
    full_name: str = Field(min_length=2, max_length=120)
    email: EmailStr
    password: str = Field(min_length=8)
    phone: str = Field(min_length=7, max_length=30)
    aadhaar_number: str = Field(pattern=r"^\d{12}$")
    role: str = Field(default="customer", pattern="^(customer|provider|admin)$")
    preferred_language: str = Field(default="en", max_length=10)
    upi_id: str | None = None
    bank_account_number: str | None = None
    bank_ifsc: str | None = None
    permanent_address: str | None = None
    residential_address: str | None = None

    @model_validator(mode="after")
    def validate_provider_details(self):
        if self.role == "provider" and not all((self.upi_id, self.bank_account_number, self.bank_ifsc, self.permanent_address, self.residential_address)):
            raise ValueError("Worker accounts require UPI, bank, permanent address, and residential address details")
        return self


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class PasswordResetRequest(BaseModel):
    email: EmailStr


class PasswordResetConfirm(BaseModel):
    token: str
    new_password: str = Field(min_length=8)


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    full_name: str
    email: EmailStr
    phone: str | None
    role: str
    preferred_language: str


class ProviderCreate(BaseModel):
    cooperative_id: int | None = None
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)
    service_radius_km: float = Field(default=15, gt=0, le=100)
    certification_details: str | None = None
    insurance_policy_number: str | None = None


class ProviderOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    verification_status: str
    latitude: float
    longitude: float
    service_radius_km: float
    available: bool
    skills: list["SkillOut"] = []


class SkillCreate(BaseModel):
    name: str = Field(min_length=2, max_length=80)
    certification: str | None = None
    years_experience: int = Field(default=0, ge=0, le=80)


class SkillOut(SkillCreate):
    model_config = ConfigDict(from_attributes=True)

    id: int


class ServiceCreate(BaseModel):
    title: str = Field(min_length=2, max_length=160)
    description: str | None = None
    category: str = Field(min_length=2, max_length=80)
    hourly_rate: float = Field(gt=0)


class ServiceOut(ServiceCreate):
    model_config = ConfigDict(from_attributes=True)

    id: int
    provider_id: int
    active: bool


class BookingCreate(BaseModel):
    provider_id: int
    service_id: int
    scheduled_for: datetime
    address: str = Field(min_length=5, max_length=300)
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)
    duration_hours: float = Field(default=1, gt=0, le=24)
    notes: str | None = None
    is_emergency: bool = False


class BookingOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    customer_id: int
    provider_id: int
    service_id: int
    scheduled_for: datetime
    address: str
    duration_hours: float
    status: str
    is_emergency: bool
    total_amount: float


class BookingStatusUpdate(BaseModel):
    status: str = Field(pattern="^(accepted|rejected|in_progress|completed|cancelled)$")


class PaymentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    booking_id: int
    amount: float
    status: str
    provider_reference: str | None
    paid_at: datetime | None


class ReviewCreate(BaseModel):
    rating: int = Field(ge=1, le=5)
    comment: str | None = None


class WelfareCreate(BaseModel):
    scheme_name: str = Field(min_length=2, max_length=160)
    valid_until: datetime | None = None
