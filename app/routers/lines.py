from typing import Annotated
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.exc import IntegrityError
from sqlmodel import Session, select
from app.database import get_session
from app.dependencies import CurrentUser, require_roles
from app.models import Plant, ProductionLine, User, UserRole
from app.schemas import ProductionLineCreate, ProductionLineRead

router = APIRouter(prefix="/api/v1/production-lines", tags=["Production Lines"])
SessionDep = Annotated[Session, Depends(get_session)]
WRITERS = require_roles(UserRole.SUPER_ADMIN, UserRole.PLANT_MANAGER, UserRole.PRODUCTION_MANAGER)


@router.post("", response_model=ProductionLineRead, status_code=201)
def create_line(data: ProductionLineCreate, session: SessionDep, user: Annotated[User, Depends(WRITERS)]):
    if session.get(Plant, data.plant_id) is None:
        raise HTTPException(status_code=404, detail="Plant not found")
    line = ProductionLine(**data.model_dump())
    session.add(line)
    try:
        session.commit()
    except IntegrityError:
        session.rollback()
        raise HTTPException(status_code=409, detail="Production line code already exists")
    session.refresh(line)
    return line


@router.get("", response_model=list[ProductionLineRead])
def list_lines(session: SessionDep, user: CurrentUser, plant_id: int | None = None):
    query = select(ProductionLine)
    if plant_id is not None:
        query = query.where(ProductionLine.plant_id == plant_id)
    return session.exec(query.order_by(ProductionLine.id.desc())).all()


@router.get("/{line_id}", response_model=ProductionLineRead)
def get_line(line_id: int, session: SessionDep, user: CurrentUser):
    item = session.get(ProductionLine, line_id)
    if item is None:
        raise HTTPException(status_code=404, detail="Production line not found")
    return item
