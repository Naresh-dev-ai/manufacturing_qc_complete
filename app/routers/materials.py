from typing import Annotated
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.exc import IntegrityError
from sqlmodel import Session, select
from app.database import get_session
from app.dependencies import CurrentUser, require_roles
from app.models import InventoryMovement, Material, MaterialStatus, MovementType, User, UserRole
from app.schemas import MaterialCreate, MaterialRead, MaterialStatusUpdate, StockMovementRequest, StockAdjustmentRequest, InventoryMovementRead

router = APIRouter(prefix="/api/v1/materials", tags=["Raw Materials"])
SessionDep = Annotated[Session, Depends(get_session)]
WRITERS = require_roles(UserRole.SUPER_ADMIN, UserRole.STORE_MANAGER)
STOCK_OPERATORS = require_roles(UserRole.SUPER_ADMIN, UserRole.STORE_MANAGER, UserRole.PRODUCTION_MANAGER, UserRole.PRODUCTION_SUPERVISOR)


def find_material(session: Session, material_id: int) -> Material:
    item = session.get(Material, material_id)
    if item is None:
        raise HTTPException(status_code=404, detail="Material not found")
    return item


def locked_material(session: Session, material_id: int) -> Material:
    item = session.exec(select(Material).where(Material.id == material_id).with_for_update()).first()
    if item is None:
        raise HTTPException(status_code=404, detail="Material not found")
    return item


def make_movement(session: Session, user: User, material: Material, kind: MovementType, delta: float, reference: str | None, remarks: str | None):
    balance = material.available_quantity + delta
    if balance < 0:
        raise HTTPException(status_code=409, detail=f"Insufficient stock. Available: {material.available_quantity} {material.unit}")
    material.available_quantity = balance
    movement = InventoryMovement(
        material_id=material.id, performed_by=user.id, movement_type=kind,
        quantity=delta, balance_after=balance, reference=reference, remarks=remarks,
    )
    session.add(material)
    session.add(movement)
    session.flush()
    return movement


@router.post("", response_model=MaterialRead, status_code=201)
def create_material(data: MaterialCreate, session: SessionDep, user: Annotated[User, Depends(WRITERS)]):
    if data.reorder_level < data.minimum_stock_level:
        raise HTTPException(status_code=422, detail="Reorder level must be at least the minimum stock level")
    item = Material(**data.model_dump())
    session.add(item)
    try:
        session.commit()
    except IntegrityError:
        session.rollback()
        raise HTTPException(status_code=409, detail="Material code already exists")
    session.refresh(item)
    return item


@router.get("", response_model=list[MaterialRead])
def list_materials(session: SessionDep, user: CurrentUser, search: str | None = None, category: str | None = None, status: MaterialStatus | None = None, low_stock_only: bool = False, page: int = Query(1, ge=1), page_size: int = Query(10, ge=1, le=100)):
    query = select(Material)
    if search:
        query = query.where(Material.name.ilike(f"%{search}%") | Material.code.ilike(f"%{search}%"))
    if category:
        query = query.where(Material.category.ilike(category))
    if status:
        query = query.where(Material.status == status)
    if low_stock_only:
        query = query.where(Material.available_quantity <= Material.reorder_level)
    query = query.order_by(Material.id.desc()).offset((page - 1) * page_size).limit(page_size)
    return session.exec(query).all()


@router.get("/{material_id}", response_model=MaterialRead)
def get_material(material_id: int, session: SessionDep, user: CurrentUser):
    return find_material(session, material_id)


@router.patch("/{material_id}/status", response_model=MaterialRead)
def set_material_status(material_id: int, data: MaterialStatusUpdate, session: SessionDep, user: Annotated[User, Depends(WRITERS)]):
    item = find_material(session, material_id)
    item.status = data.status
    session.add(item)
    session.commit()
    session.refresh(item)
    return item


@router.post("/{material_id}/stock-in", response_model=InventoryMovementRead, status_code=201)
def stock_in(material_id: int, data: StockMovementRequest, session: SessionDep, user: Annotated[User, Depends(STOCK_OPERATORS)]):
    try:
        item = locked_material(session, material_id)
        if item.status != MaterialStatus.ACTIVE:
            raise HTTPException(status_code=409, detail="Material is not active")
        movement = make_movement(session, user, item, MovementType.STOCK_IN, data.quantity, data.reference, data.remarks)
        session.commit()
        session.refresh(movement)
        return movement
    except Exception:
        session.rollback()
        raise


@router.post("/{material_id}/stock-out", response_model=InventoryMovementRead, status_code=201)
def stock_out(material_id: int, data: StockMovementRequest, session: SessionDep, user: Annotated[User, Depends(STOCK_OPERATORS)]):
    try:
        item = locked_material(session, material_id)
        if item.status != MaterialStatus.ACTIVE:
            raise HTTPException(status_code=409, detail="Material is not active")
        movement = make_movement(session, user, item, MovementType.STOCK_OUT, -data.quantity, data.reference, data.remarks)
        session.commit()
        session.refresh(movement)
        return movement
    except Exception:
        session.rollback()
        raise


@router.post("/{material_id}/adjustment", response_model=InventoryMovementRead, status_code=201)
def adjust_stock(material_id: int, data: StockAdjustmentRequest, session: SessionDep, user: Annotated[User, Depends(WRITERS)]):
    if data.quantity_change == 0:
        raise HTTPException(status_code=422, detail="Adjustment cannot be zero")
    try:
        item = locked_material(session, material_id)
        movement = make_movement(session, user, item, MovementType.ADJUSTMENT, data.quantity_change, data.reference, data.remarks)
        session.commit()
        session.refresh(movement)
        return movement
    except Exception:
        session.rollback()
        raise


@router.get("/{material_id}/movements", response_model=list[InventoryMovementRead])
def movement_history(material_id: int, session: SessionDep, user: CurrentUser, page: int = Query(1, ge=1), page_size: int = Query(10, ge=1, le=100)):
    find_material(session, material_id)
    query = select(InventoryMovement).where(InventoryMovement.material_id == material_id).order_by(InventoryMovement.id.desc()).offset((page - 1) * page_size).limit(page_size)
    return session.exec(query).all()
