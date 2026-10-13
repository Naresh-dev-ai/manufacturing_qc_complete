from typing import Annotated
from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select
from app.database import get_session
from app.dependencies import CurrentUser, require_roles
from app.models import BOMItem, Material, Product, User, UserRole
from app.schemas import BOMItemCreate, BOMItemRead, MaterialRequirement

router = APIRouter(prefix="/api/v1/products", tags=["Bill of Materials"])
SessionDep = Annotated[Session, Depends(get_session)]
WRITERS = require_roles(UserRole.SUPER_ADMIN, UserRole.PRODUCTION_MANAGER)


@router.post("/{product_id}/bom", response_model=BOMItemRead, status_code=201)
def add_bom_item(product_id: int, data: BOMItemCreate, session: SessionDep, user: Annotated[User, Depends(WRITERS)]):
    if session.get(Product, product_id) is None:
        raise HTTPException(status_code=404, detail="Product not found")
    if session.get(Material, data.material_id) is None:
        raise HTTPException(status_code=404, detail="Material not found")
    existing = session.exec(select(BOMItem).where(BOMItem.product_id == product_id, BOMItem.material_id == data.material_id)).first()
    if existing:
        raise HTTPException(status_code=409, detail="This material is already in the product BOM; update is not supported in this starter")
    item = BOMItem(product_id=product_id, **data.model_dump())
    session.add(item)
    session.commit()
    session.refresh(item)
    return item


@router.get("/{product_id}/bom", response_model=list[BOMItemRead])
def list_bom(product_id: int, session: SessionDep, user: CurrentUser):
    if session.get(Product, product_id) is None:
        raise HTTPException(status_code=404, detail="Product not found")
    return session.exec(select(BOMItem).where(BOMItem.product_id == product_id).order_by(BOMItem.id)).all()


@router.get("/{product_id}/material-requirements", response_model=list[MaterialRequirement])
def material_requirements(product_id: int, quantity: int, session: SessionDep, user: CurrentUser):
    if quantity < 1:
        raise HTTPException(status_code=422, detail="quantity must be at least 1")
    if session.get(Product, product_id) is None:
        raise HTTPException(status_code=404, detail="Product not found")
    rows = session.exec(select(BOMItem).where(BOMItem.product_id == product_id)).all()
    result = []
    for row in rows:
        material = session.get(Material, row.material_id)
        required = row.quantity_per_product * quantity * (1 + row.scrap_percent / 100)
        result.append(MaterialRequirement(
            material_id=material.id,
            material_code=material.code,
            material_name=material.name,
            unit=material.unit,
            quantity_per_product=row.quantity_per_product,
            scrap_percent=row.scrap_percent,
            required_quantity=round(required, 4),
            available_quantity=material.available_quantity,
            sufficient=material.available_quantity >= required,
        ))
    return result
