from typing import Annotated
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.exc import IntegrityError
from sqlmodel import Session, select
from app.database import get_session
from app.dependencies import CurrentUser, require_roles
from app.models import InspectionDecision, ProductionOrder, ProductionOrderStatus, QualityInspection, User, UserRole
from app.schemas import QualityInspectionCreate, QualityInspectionRead

router = APIRouter(prefix="/api/v1/quality-inspections", tags=["Quality Control"])
SessionDep = Annotated[Session, Depends(get_session)]
INSPECTORS = require_roles(UserRole.SUPER_ADMIN, UserRole.QUALITY_INSPECTOR)


@router.post("", response_model=QualityInspectionRead, status_code=201)
def create_inspection(data: QualityInspectionCreate, session: SessionDep, user: Annotated[User, Depends(INSPECTORS)]):
    order = session.get(ProductionOrder, data.production_order_id)
    if order is None:
        raise HTTPException(status_code=404, detail="Production order not found")
    if order.status != ProductionOrderStatus.COMPLETED:
        raise HTTPException(status_code=409, detail="Quality inspection requires a completed production order")
    if data.quantity_passed + data.quantity_failed != data.quantity_inspected:
        raise HTTPException(status_code=422, detail="Passed quantity plus failed quantity must equal inspected quantity")
    if data.decision == InspectionDecision.PASS and data.quantity_failed > 0:
        raise HTTPException(status_code=422, detail="Decision cannot be pass when failed quantity is greater than zero")
    if data.decision == InspectionDecision.FAIL and data.quantity_failed == 0:
        raise HTTPException(status_code=422, detail="Decision cannot be fail when no failed units are recorded")
    item = QualityInspection(**data.model_dump(), inspected_by=user.id)
    session.add(item)
    try:
        session.commit()
    except IntegrityError:
        session.rollback()
        raise HTTPException(status_code=409, detail="Inspection number already exists")
    session.refresh(item)
    return item


@router.get("", response_model=list[QualityInspectionRead])
def list_inspections(session: SessionDep, user: CurrentUser, decision: InspectionDecision | None = None):
    query = select(QualityInspection)
    if decision:
        query = query.where(QualityInspection.decision == decision)
    return session.exec(query.order_by(QualityInspection.id.desc())).all()


@router.get("/{inspection_id}", response_model=QualityInspectionRead)
def get_inspection(inspection_id: int, session: SessionDep, user: CurrentUser):
    item = session.get(QualityInspection, inspection_id)
    if item is None:
        raise HTTPException(status_code=404, detail="Quality inspection not found")
    return item
