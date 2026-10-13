from datetime import datetime, timezone
from typing import Annotated
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.exc import IntegrityError
from sqlmodel import Session, select
from app.database import get_session
from app.dependencies import CurrentUser, require_roles
from app.models import BOMItem, InventoryMovement, Material, MaterialStatus, MovementType, ProductionLine, Product, ProductionOrder, ProductionOrderStatus, User, UserRole, utc_now
from app.schemas import ProductionOrderCreate, ProductionOrderRead, ProductionCompletion

router = APIRouter(prefix="/api/v1/production-orders", tags=["Production Orders"])
SessionDep = Annotated[Session, Depends(get_session)]
PLANNERS = require_roles(UserRole.SUPER_ADMIN, UserRole.PRODUCTION_MANAGER, UserRole.PLANT_MANAGER)
OPERATORS = require_roles(UserRole.SUPER_ADMIN, UserRole.PRODUCTION_MANAGER, UserRole.PRODUCTION_SUPERVISOR)


@router.post("", response_model=ProductionOrderRead, status_code=201)
def create_order(data: ProductionOrderCreate, session: SessionDep, user: Annotated[User, Depends(PLANNERS)]):
    if session.get(Product, data.product_id) is None:
        raise HTTPException(status_code=404, detail="Product not found")
    if session.get(ProductionLine, data.production_line_id) is None:
        raise HTTPException(status_code=404, detail="Production line not found")
    order = ProductionOrder(**data.model_dump(), created_by=user.id)
    session.add(order)
    try:
        session.commit()
    except IntegrityError:
        session.rollback()
        raise HTTPException(status_code=409, detail="Production order number already exists")
    session.refresh(order)
    return order


@router.get("", response_model=list[ProductionOrderRead])
def list_orders(session: SessionDep, user: CurrentUser, status_filter: ProductionOrderStatus | None = None):
    query = select(ProductionOrder)
    if status_filter:
        query = query.where(ProductionOrder.status == status_filter)
    return session.exec(query.order_by(ProductionOrder.id.desc())).all()


@router.get("/{order_id}", response_model=ProductionOrderRead)
def get_order(order_id: int, session: SessionDep, user: CurrentUser):
    order = session.get(ProductionOrder, order_id)
    if order is None:
        raise HTTPException(status_code=404, detail="Production order not found")
    return order


@router.post("/{order_id}/start", response_model=ProductionOrderRead)
def start_order(order_id: int, session: SessionDep, user: Annotated[User, Depends(OPERATORS)]):
    try:
        order = session.exec(select(ProductionOrder).where(ProductionOrder.id == order_id).with_for_update()).first()
        if order is None:
            raise HTTPException(status_code=404, detail="Production order not found")
        if order.status != ProductionOrderStatus.DRAFT:
            raise HTTPException(status_code=409, detail="Only draft orders can be started")
        bom = session.exec(select(BOMItem).where(BOMItem.product_id == order.product_id)).all()
        if not bom:
            raise HTTPException(status_code=409, detail="Cannot start production: product has no BOM")
        locked_materials = []
        for row in bom:
            material = session.exec(select(Material).where(Material.id == row.material_id).with_for_update()).first()
            if material is None or material.status != MaterialStatus.ACTIVE:
                raise HTTPException(status_code=409, detail=f"Material {row.material_id} is missing or inactive")
            required = row.quantity_per_product * order.planned_quantity * (1 + row.scrap_percent / 100)
            if material.available_quantity < required:
                raise HTTPException(status_code=409, detail=f"Insufficient {material.name}: need {required:.4f} {material.unit}, have {material.available_quantity}")
            locked_materials.append((material, required))
        # Deduct all BOM materials in the same database transaction.
        for material, required in locked_materials:
            material.available_quantity -= required
            session.add(material)
            session.add(InventoryMovement(
                material_id=material.id,
                performed_by=user.id,
                movement_type=MovementType.STOCK_OUT,
                quantity=-required,
                balance_after=material.available_quantity,
                reference=order.order_number,
                remarks=f"Materials issued to production order {order.order_number}",
            ))
        order.status = ProductionOrderStatus.IN_PROGRESS
        order.started_at = utc_now()
        session.add(order)
        session.commit()
        session.refresh(order)
        return order
    except Exception:
        session.rollback()
        raise


@router.post("/{order_id}/complete", response_model=ProductionOrderRead)
def complete_order(order_id: int, data: ProductionCompletion, session: SessionDep, user: Annotated[User, Depends(OPERATORS)]):
    order = session.get(ProductionOrder, order_id)
    if order is None:
        raise HTTPException(status_code=404, detail="Production order not found")
    if order.status != ProductionOrderStatus.IN_PROGRESS:
        raise HTTPException(status_code=409, detail="Only in-progress orders can be completed")
    if data.produced_quantity > order.planned_quantity:
        raise HTTPException(status_code=422, detail="Produced quantity cannot exceed planned quantity in this version")
    order.produced_quantity = data.produced_quantity
    order.status = ProductionOrderStatus.COMPLETED
    order.completed_at = utc_now()
    session.add(order)
    session.commit()
    session.refresh(order)
    return order


@router.post("/{order_id}/cancel", response_model=ProductionOrderRead)
def cancel_order(order_id: int, session: SessionDep, user: Annotated[User, Depends(PLANNERS)]):
    order = session.get(ProductionOrder, order_id)
    if order is None:
        raise HTTPException(status_code=404, detail="Production order not found")
    if order.status != ProductionOrderStatus.DRAFT:
        raise HTTPException(status_code=409, detail="Only draft orders can be cancelled")
    order.status = ProductionOrderStatus.CANCELLED
    session.add(order)
    session.commit()
    session.refresh(order)
    return order
