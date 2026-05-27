from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.customer import CustomerProfile
from app.schemas.customer import CustomerProfileCreate, CustomerRegistrationResponse


router = APIRouter(prefix="/api/customers", tags=["customers"])


@router.post(
    "/register",
    response_model=CustomerRegistrationResponse,
    status_code=status.HTTP_201_CREATED,
)
def register_customer(payload: CustomerProfileCreate, db: Session = Depends(get_db)):
    normalized_email = payload.email.lower()
    existing_customer = db.scalar(
        select(CustomerProfile).where(CustomerProfile.email == normalized_email)
    )

    if existing_customer is not None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A customer profile with this email already exists",
        )

    customer = CustomerProfile(
        full_name=payload.full_name.strip(),
        email=normalized_email,
        phone_number=payload.phone_number.strip(),
        birth_day=payload.birth_day,
        address=payload.address.strip(),
        city=payload.city.strip(),
        pin_code=payload.pin_code.strip(),
        style_notes=payload.style_notes.strip(),
        consent_given=payload.consent_given,
    )

    db.add(customer)
    db.commit()
    db.refresh(customer)

    return {
        "message": "Customer profile registered successfully",
        "customer": customer,
    }
