from typing import Annotated
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.exc import IntegrityError
from sqlmodel import Session, select
from app.database import get_session
from app.dependencies import CurrentUser, require_roles
from app.models import Plant, User, UserRole
from app.schemas import PlantCreate, PlantRead

router = APIRouter(prefix="/api/v1/plants", tags=["Plants"])
SessionDep = Annotated[Session, Depends(get_session)]
WRITERS = require_roles(UserRole.SUPER_ADMIN, UserRole.PLANT_MANAGER)


@router.post("", response_model=PlantRead, status_code=201)
def create_plant(data: PlantCreate, session: SessionDep, user: Annotated[User, Depends(WRITERS)]):
    plant = Plant(**data.model_dump())
    session.add(plant)
    try:
        session.commit()
    except IntegrityError:
        session.rollback()
        raise HTTPException(status_code=409, detail="Plant code already exists")
    session.refresh(plant)
    return plant


@router.get("", response_model=list[PlantRead])
def list_plants(session: SessionDep, user: CurrentUser):
    return session.exec(select(Plant).order_by(Plant.id.desc())).all()


@router.get("/{plant_id}", response_model=PlantRead)
def get_plant(plant_id: int, session: SessionDep, user: CurrentUser):
    item = session.get(Plant, plant_id)
    if item is None:
        raise HTTPException(status_code=404, detail="Plant not found")
    return item
