from datetime import datetime, timezone
import math
import uuid
from pathlib import Path

from fastapi import Depends, FastAPI, HTTPException, Query, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from .auth import create_access_token, create_password_reset_token, get_current_user, get_reset_user, hash_password, require_roles, verify_password
from .database import Base, engine, ensure_user_columns, get_db
from .models import Booking, Cooperative, Payment, Provider, Review, Service, Skill, User, WelfareRecord
from .schemas import (
    BookingCreate, BookingOut, BookingStatusUpdate, PaymentOut, ProviderCreate, ProviderOut,
    ReviewCreate, ServiceCreate, ServiceOut, SkillCreate, SkillOut, Token, UserCreate, UserOut,
    WelfareCreate, PasswordResetConfirm, PasswordResetRequest,
)

Base.metadata.create_all(bind=engine)
ensure_user_columns()
app = FastAPI(title="Sahaayak Cooperative Services API", version="1.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def distance_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    radius = 6371
    lat_delta = math.radians(lat2 - lat1)
    lon_delta = math.radians(lon2 - lon1)
    a = math.sin(lat_delta / 2) ** 2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(lon_delta / 2) ** 2
    return radius * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "service": "sahaayak-api"}


@app.post("/auth/register", response_model=UserOut, status_code=201)
def register(payload: UserCreate, db: Session = Depends(get_db)):
    if db.scalar(select(User).where(User.email == payload.email.lower())):
        raise HTTPException(status_code=409, detail="Email is already registered")
    user = User(
        full_name=payload.full_name,
        email=payload.email.lower(),
        phone=payload.phone,
        aadhaar_number=payload.aadhaar_number,
        upi_id=payload.upi_id,
        bank_account_number=payload.bank_account_number,
        bank_ifsc=payload.bank_ifsc,
        permanent_address=payload.permanent_address,
        residential_address=payload.residential_address,
        password_hash=hash_password(payload.password),
        role=payload.role,
        preferred_language=payload.preferred_language,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@app.post("/auth/login", response_model=Token)
def login(form: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = db.scalar(select(User).where(User.email == form.username.lower()))
    if not user or not verify_password(form.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Incorrect email or password")
    return Token(access_token=create_access_token(user.id))


@app.post("/auth/forgot-password")
def forgot_password(payload: PasswordResetRequest, db: Session = Depends(get_db)):
    user = db.scalar(select(User).where(User.email == payload.email.lower()))
    if not user:
        raise HTTPException(status_code=404, detail="No account found for this email")
    return {"message": "Reset token created", "reset_token": create_password_reset_token(user.id)}


@app.post("/auth/reset-password")
def reset_password(payload: PasswordResetConfirm, db: Session = Depends(get_db)):
    user = get_reset_user(payload.token, db)
    user.password_hash = hash_password(payload.new_password)
    db.commit()
    return {"message": "Password reset successfully"}


@app.get("/auth/me", response_model=UserOut)
def me(user: User = Depends(get_current_user)):
    return user


@app.post("/providers", response_model=ProviderOut, status_code=201)
def create_provider(
    payload: ProviderCreate,
    user: User = Depends(require_roles("provider")),
    db: Session = Depends(get_db),
):
    if user.provider_profile:
        raise HTTPException(status_code=409, detail="Provider profile already exists")
    if payload.cooperative_id and not db.get(Cooperative, payload.cooperative_id):
        raise HTTPException(status_code=404, detail="Cooperative not found")
    provider = Provider(user_id=user.id, **payload.model_dump())
    db.add(provider)
    db.commit()
    db.refresh(provider)
    return provider


@app.post("/providers/me/skills", response_model=SkillOut, status_code=201)
def add_skill(
    payload: SkillCreate,
    provider_user: User = Depends(require_roles("provider")),
    db: Session = Depends(get_db),
):
    provider = provider_user.provider_profile
    if not provider:
        raise HTTPException(status_code=400, detail="Create a provider profile first")
    skill = Skill(provider_id=provider.id, **payload.model_dump())
    db.add(skill)
    db.commit()
    db.refresh(skill)
    return skill


@app.post("/providers/me/services", response_model=ServiceOut, status_code=201)
def add_service(
    payload: ServiceCreate,
    provider_user: User = Depends(require_roles("provider")),
    db: Session = Depends(get_db),
):
    provider = provider_user.provider_profile
    if not provider or provider.verification_status != "verified":
        raise HTTPException(status_code=403, detail="Provider must be verified before listing services")
    service = Service(provider_id=provider.id, **payload.model_dump())
    db.add(service)
    db.commit()
    db.refresh(service)
    return service


@app.get("/services", response_model=list[ServiceOut])
def search_services(
    category: str | None = None,
    skill: str | None = None,
    latitude: float | None = Query(default=None, ge=-90, le=90),
    longitude: float | None = Query(default=None, ge=-180, le=180),
    radius_km: float = Query(default=25, gt=0, le=100),
    db: Session = Depends(get_db),
):
    query = select(Service).where(Service.active.is_(True)).join(Provider).where(
        Provider.verification_status == "verified", Provider.available.is_(True)
    )
    if category:
        query = query.where(Service.category.ilike(category))
    if skill:
        query = query.join(Skill, Skill.provider_id == Provider.id).where(Skill.name.ilike(f"%{skill}%"))
    services = list(db.scalars(query).unique())
    if latitude is None or longitude is None:
        return services
    return [
        service for service in services
        if (provider := db.get(Provider, service.provider_id))
        and distance_km(latitude, longitude, provider.latitude, provider.longitude) <= radius_km
    ]


@app.post("/bookings", response_model=BookingOut, status_code=201)
def create_booking(
    payload: BookingCreate,
    customer: User = Depends(require_roles("customer")),
    db: Session = Depends(get_db),
):
    service = db.get(Service, payload.service_id)
    provider = db.get(Provider, payload.provider_id)
    if not service or service.provider_id != payload.provider_id or not service.active:
        raise HTTPException(status_code=404, detail="Active service not found for this provider")
    if not provider or provider.verification_status != "verified" or not provider.available:
        raise HTTPException(status_code=400, detail="Provider is not currently available")
    total = service.hourly_rate * payload.duration_hours
    if payload.is_emergency:
        total *= 1.25
    booking = Booking(customer_id=customer.id, total_amount=round(total, 2), **payload.model_dump())
    db.add(booking)
    db.commit()
    db.refresh(booking)
    return booking


@app.get("/bookings", response_model=list[BookingOut])
def list_bookings(
    user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    query = select(Booking)
    if user.role == "customer":
        query = query.where(Booking.customer_id == user.id)
    elif user.role == "provider":
        provider = user.provider_profile
        if not provider:
            return []
        query = query.where(Booking.provider_id == provider.id)
    return list(db.scalars(query.order_by(Booking.created_at.desc())))


@app.patch("/bookings/{booking_id}", response_model=BookingOut)
def update_booking(
    booking_id: int,
    payload: BookingStatusUpdate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    booking = db.get(Booking, booking_id)
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")
    provider = user.provider_profile
    allowed = user.role == "admin" or booking.customer_id == user.id or (provider and booking.provider_id == provider.id)
    if not allowed:
        raise HTTPException(status_code=403, detail="You cannot update this booking")
    if booking.status in {"completed", "cancelled"}:
        raise HTTPException(status_code=409, detail="Closed bookings cannot be changed")
    booking.status = payload.status
    db.commit()
    db.refresh(booking)
    return booking


@app.post("/bookings/{booking_id}/pay", response_model=PaymentOut, status_code=201)
def pay_booking(
    booking_id: int,
    customer: User = Depends(require_roles("customer")),
    db: Session = Depends(get_db),
):
    booking = db.get(Booking, booking_id)
    if not booking or booking.customer_id != customer.id:
        raise HTTPException(status_code=404, detail="Booking not found")
    if booking.status == "cancelled":
        raise HTTPException(status_code=409, detail="Cancelled bookings cannot be paid")
    if db.scalar(select(Payment).where(Payment.booking_id == booking_id)):
        raise HTTPException(status_code=409, detail="Booking is already paid")
    payment = Payment(booking_id=booking_id, amount=booking.total_amount, status="paid", provider_reference=f"DEMO-{uuid.uuid4().hex[:12].upper()}", paid_at=datetime.now(timezone.utc))
    db.add(payment)
    db.commit()
    db.refresh(payment)
    return payment


@app.post("/bookings/{booking_id}/review", status_code=201)
def review_booking(
    booking_id: int,
    payload: ReviewCreate,
    customer: User = Depends(require_roles("customer")),
    db: Session = Depends(get_db),
):
    booking = db.get(Booking, booking_id)
    if not booking or booking.customer_id != customer.id:
        raise HTTPException(status_code=404, detail="Booking not found")
    if booking.status != "completed":
        raise HTTPException(status_code=400, detail="Only completed bookings can be reviewed")
    if db.scalar(select(Review).where(Review.booking_id == booking_id)):
        raise HTTPException(status_code=409, detail="Booking already reviewed")
    review = Review(booking_id=booking.id, customer_id=customer.id, provider_id=booking.provider_id, **payload.model_dump())
    db.add(review)
    db.commit()
    return {"id": review.id, "message": "Review recorded"}


@app.post("/providers/me/welfare", status_code=201)
def add_welfare(
    payload: WelfareCreate,
    provider_user: User = Depends(require_roles("provider")),
    db: Session = Depends(get_db),
):
    provider = provider_user.provider_profile
    if not provider:
        raise HTTPException(status_code=400, detail="Create a provider profile first")
    record = WelfareRecord(provider_id=provider.id, **payload.model_dump())
    db.add(record)
    db.commit()
    db.refresh(record)
    return {"id": record.id, "scheme_name": record.scheme_name, "status": record.status}


@app.post("/admin/cooperatives", status_code=201)
def create_cooperative(
    name: str, registration_number: str, district: str,
    _: User = Depends(require_roles("admin")), db: Session = Depends(get_db),
):
    cooperative = Cooperative(name=name, registration_number=registration_number, district=district)
    db.add(cooperative)
    db.commit()
    db.refresh(cooperative)
    return cooperative


@app.patch("/admin/providers/{provider_id}/verify", response_model=ProviderOut)
def verify_provider(
    provider_id: int,
    _: User = Depends(require_roles("admin")), db: Session = Depends(get_db),
):
    provider = db.get(Provider, provider_id)
    if not provider:
        raise HTTPException(status_code=404, detail="Provider not found")
    provider.verification_status = "verified"
    db.commit()
    db.refresh(provider)
    return provider


@app.get("/admin/dashboard")
def dashboard(_: User = Depends(require_roles("admin")), db: Session = Depends(get_db)):
    return {
        "customers": db.scalar(select(func.count(User.id)).where(User.role == "customer")) or 0,
        "providers": db.scalar(select(func.count(Provider.id))) or 0,
        "verified_providers": db.scalar(select(func.count(Provider.id)).where(Provider.verification_status == "verified")) or 0,
        "active_services": db.scalar(select(func.count(Service.id)).where(Service.active.is_(True))) or 0,
        "bookings": db.scalar(select(func.count(Booking.id))) or 0,
        "completed_bookings": db.scalar(select(func.count(Booking.id)).where(Booking.status == "completed")) or 0,
        "revenue": db.scalar(select(func.coalesce(func.sum(Payment.amount), 0))) or 0,
    }


@app.get("/admin/demand-forecast")
def demand_forecast(_: User = Depends(require_roles("admin")), db: Session = Depends(get_db)):
    rows = db.execute(select(Service.category, func.count(Booking.id)).join(Booking, Booking.service_id == Service.id, isouter=True).group_by(Service.category).order_by(func.count(Booking.id).desc())).all()
    return [{"category": category, "bookings": count, "recommended_capacity": max(1, math.ceil(count * 1.2))} for category, count in rows]


frontend_directory = Path(__file__).resolve().parent.parent / "frontend"
if frontend_directory.is_dir():
    app.mount("/", StaticFiles(directory=frontend_directory, html=True), name="frontend")
