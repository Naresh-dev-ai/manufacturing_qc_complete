from contextlib import asynccontextmanager
from fastapi import FastAPI
from sqlmodel import Session, SQLModel, select

# Import models first so SQLModel registers every table.
from app import models
from app.config import settings
from app.database import engine
from app.models import User, UserRole
from app.security import hash_password
from app.routers import auth, bom, lines, materials, plants, products, production, quality, reports


def initialize_database() -> None:
    # Beginner-friendly bootstrap. Use Alembic migrations for managed deployments.
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        if session.exec(select(User)).first() is None:
            session.add(User(
                username=settings.initial_admin_username,
                full_name="Initial Administrator",
                password_hash=hash_password(settings.initial_admin_password),
                role=UserRole.SUPER_ADMIN,
            ))
            session.commit()


@asynccontextmanager
async def lifespan(app: FastAPI):
    initialize_database()
    yield


app = FastAPI(
    title="Manufacturing Production & Quality Control API",
    description="Plants, products, inventory, BOM, production orders, quality inspections, and reports.",
    version="2.0.0",
    lifespan=lifespan,
)


@app.get("/", tags=["Health"])
def root():
    return {"message": "Manufacturing Production & Quality Control API is running", "docs": "/docs", "health": "/health"}


@app.get("/health", tags=["Health"])
def health():
    return {"status": "ok"}


app.include_router(auth.router)
app.include_router(plants.router)
app.include_router(lines.router)
app.include_router(products.router)
app.include_router(materials.router)
app.include_router(bom.router)
app.include_router(production.router)
app.include_router(quality.router)
app.include_router(reports.router)
