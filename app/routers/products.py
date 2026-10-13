from typing import Annotated
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.exc import IntegrityError
from sqlmodel import Session, select
from app.database import get_session
from app.dependencies import CurrentUser, require_roles
from app.models import Product, User, UserRole
from app.schemas import ProductCreate, ProductRead

router = APIRouter(prefix="/api/v1/products", tags=["Products"])
SessionDep = Annotated[Session, Depends(get_session)]
WRITERS = require_roles(UserRole.SUPER_ADMIN, UserRole.PRODUCTION_MANAGER)


@router.post("", response_model=ProductRead, status_code=201)
def create_product(data: ProductCreate, session: SessionDep, user: Annotated[User, Depends(WRITERS)]):
    product = Product(**data.model_dump())
    session.add(product)
    try:
        session.commit()
    except IntegrityError:
        session.rollback()
        raise HTTPException(status_code=409, detail="Product code already exists")
    session.refresh(product)
    return product


@router.get("", response_model=list[ProductRead])
def list_products(session: SessionDep, user: CurrentUser):
    return session.exec(select(Product).order_by(Product.id.desc())).all()


@router.get("/{product_id}", response_model=ProductRead)
def get_product(product_id: int, session: SessionDep, user: CurrentUser):
    item = session.get(Product, product_id)
    if item is None:
        raise HTTPException(status_code=404, detail="Product not found")
    return item
