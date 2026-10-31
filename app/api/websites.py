
import ipaddress
from urllib.parse import urlsplit

from fastapi import APIRouter, Depends, HTTPException, Response, status
from pydantic import BaseModel, ConfigDict, Field, field_validator
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models import Website


router = APIRouter(prefix="/api/v1/websites", tags=["Websites"])


def validate_website_url(value: str) -> str:
    if len(value) > 2048:
        raise ValueError("URL must not exceed 2048 characters")

    parsed = urlsplit(value)

    if parsed.scheme not in {"http", "https"}:
        raise ValueError("Only HTTP and HTTPS URLs are allowed")

    if not parsed.hostname:
        raise ValueError("A valid hostname is required")

    if parsed.username or parsed.password:
        raise ValueError("URLs must not contain credentials")

    hostname = parsed.hostname.rstrip(".").lower()

    if hostname == "localhost" or hostname.endswith(
        (".localhost", ".local")
    ):
        raise ValueError("Local hostnames are not allowed")

    try:
        address = ipaddress.ip_address(hostname)
    except ValueError:
        address = None

    if address is not None and not address.is_global:
        raise ValueError("Private or non-public IP addresses are not allowed")

    return value


class WebsiteCreate(BaseModel):
    name: str = Field(min_length=1, max_length=150)
    url: str

    @field_validator("url")
    @classmethod
    def validate_url(cls, value: str) -> str:
        return validate_website_url(value)


class WebsiteUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=150)
    url: str | None = None
    is_active: bool | None = None

    @field_validator("url")
    @classmethod
    def validate_url(cls, value: str | None) -> str | None:
        if value is not None:
            return validate_website_url(value)
        return value


class WebsiteRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    url: str
    is_active: bool


@router.post(
    "",
    response_model=WebsiteRead,
    status_code=status.HTTP_201_CREATED,
)
def create_website(
    payload: WebsiteCreate,
    db: Session = Depends(get_db),
):
    website = Website(**payload.model_dump())

    db.add(website)

    try:
        db.commit()
        db.refresh(website)
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A website with this URL already exists",
        )

    return website


@router.get("", response_model=list[WebsiteRead])
def list_websites(db: Session = Depends(get_db)):
    return db.scalars(
        select(Website).order_by(Website.id)
    ).all()


@router.get("/{website_id}", response_model=WebsiteRead)
def get_website(
    website_id: int,
    db: Session = Depends(get_db),
):
    website = db.get(Website, website_id)

    if website is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Website not found",
        )

    return website


@router.patch("/{website_id}", response_model=WebsiteRead)
def update_website(
    website_id: int,
    payload: WebsiteUpdate,
    db: Session = Depends(get_db),
):
    website = db.get(Website, website_id)

    if website is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Website not found",
        )

    updates = payload.model_dump(exclude_unset=True)

    for field, value in updates.items():
        setattr(website, field, value)

    try:
        db.commit()
        db.refresh(website)
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A website with this URL already exists",
        )

    return website


@router.delete(
    "/{website_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_website(
    website_id: int,
    db: Session = Depends(get_db),
):
    website = db.get(Website, website_id)

    if website is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Website not found",
        )

    db.delete(website)
    db.commit()

    return Response(status_code=status.HTTP_204_NO_CONTENT)
