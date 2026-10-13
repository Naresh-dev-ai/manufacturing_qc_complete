from fastapi import APIRouter, Depends
from sqlmodel import Session, select
from app.database import get_session
from app.dependencies import CurrentUser, SessionDep
from app.models import InventoryMovement, Material, ProductionOrder, ProductionOrderStatus, QualityInspection, InspectionDecision

router = APIRouter(prefix="/api/v1/reports", tags=["Reports"])


@router.get("/dashboard")
def dashboard(session: SessionDep, user: CurrentUser):
    materials = session.exec(select(Material)).all()
    orders = session.exec(select(ProductionOrder)).all()
    inspections = session.exec(select(QualityInspection)).all()
    return {
        "materials_count": len(materials),
        "low_stock_count": sum(1 for m in materials if m.available_quantity <= m.reorder_level),
        "production_orders_count": len(orders),
        "orders_in_progress": sum(1 for o in orders if o.status == ProductionOrderStatus.IN_PROGRESS),
        "orders_completed": sum(1 for o in orders if o.status == ProductionOrderStatus.COMPLETED),
        "inspections_count": len(inspections),
        "failed_inspections": sum(1 for i in inspections if i.decision == InspectionDecision.FAIL),
    }


@router.get("/inventory-movements")
def inventory_movements_report(session: SessionDep, user: CurrentUser):
    rows = session.exec(select(InventoryMovement).order_by(InventoryMovement.id.desc()).limit(200)).all()
    return [
        {
            "id": row.id,
            "material_id": row.material_id,
            "movement_type": row.movement_type.value,
            "quantity": row.quantity,
            "balance_after": row.balance_after,
            "reference": row.reference,
            "created_at": row.created_at,
        }
        for row in rows
    ]


@router.get("/production")
def production_report(session: SessionDep, user: CurrentUser):
    orders = session.exec(select(ProductionOrder)).all()
    return {
        "total_orders": len(orders),
        "planned_units": sum(o.planned_quantity for o in orders),
        "produced_units": sum(o.produced_quantity for o in orders),
        "completed_orders": sum(1 for o in orders if o.status == ProductionOrderStatus.COMPLETED),
        "in_progress_orders": sum(1 for o in orders if o.status == ProductionOrderStatus.IN_PROGRESS),
    }


@router.get("/quality")
def quality_report(session: SessionDep, user: CurrentUser):
    inspections = session.exec(select(QualityInspection)).all()
    inspected = sum(i.quantity_inspected for i in inspections)
    failed = sum(i.quantity_failed for i in inspections)
    return {
        "inspection_count": len(inspections),
        "units_inspected": inspected,
        "units_passed": sum(i.quantity_passed for i in inspections),
        "units_failed": failed,
        "defect_rate_percent": round((failed / inspected * 100), 2) if inspected else 0.0,
    }
