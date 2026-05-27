from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class CustomerProfileCreate(BaseModel):
    full_name: str = Field(min_length=2, max_length=160)
    email: EmailStr = Field(max_length=255)
    phone_number: str = Field(min_length=7, max_length=40)
    birth_day: date
    address: str = Field(min_length=5, max_length=500)
    city: str = Field(min_length=2, max_length=120)
    pin_code: str = Field(min_length=3, max_length=40)
    style_notes: str = Field(min_length=1, max_length=2000)
    consent_given: bool


class CustomerProfileRead(BaseModel):
    id: int
    full_name: str
    email: EmailStr
    phone_number: str
    birth_day: date
    address: str
    city: str
    pin_code: str
    style_notes: str
    consent_given: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class CustomerRegistrationResponse(BaseModel):
    message: str
    customer: CustomerProfileRead
