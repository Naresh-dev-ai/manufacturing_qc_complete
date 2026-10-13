from datetime import datetime, timezone
from enum import Enum
from typing import Optional
from sqlmodel import SQLModel, Field


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class UserRole(str, Enum):
    SUPER_ADMIN = "super_admin"
    PLANT_MANAGER = "plant_manager"
    PRODUCTION_MANAGER = "production_manager"
    PRODUCTION_SUPERVISOR = "production_supervisor"
    QUALITY_INSPECTOR = "quality_inspector"
    STORE_MANAGER = "store_manager"
    WORKER = "worker"


class MaterialStatus(str, Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    DISCONTINUED = "discontinued"


class MovementType(str, Enum):
    STOCK_IN = "stock_in"
    STOCK_OUT = "stock_out"
    ADJUSTMENT = "adjustment"


class ProductionOrderStatus(str, Enum):
    DRAFT = "draft"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class InspectionDecision(str, Enum):
    PASS = "pass"
    FAIL = "fail"
    CONDITIONAL = "conditional"


class User(SQLModel, table=True):
    __tablename__ = "users"
    id: Optional[int] = Field(default=None, primary_key=True)
    username: str = Field(index=True, unique=True, max_length=80)
    full_name: str = Field(max_length=150)
    password_hash: str
    role: UserRole = Field(default=UserRole.WORKER, index=True)
    is_active: bool = Field(default=True, index=True)
    created_at: datetime = Field(default_factory=utc_now)


class Plant(SQLModel, table=True):
    __tablename__ = "plants"
    id: Optional[int] = Field(default=None, primary_key=True)
    code: str = Field(index=True, unique=True, max_length=40)
    name: str = Field(index=True, max_length=150)
    address: Optional[str] = Field(default=None, max_length=300)
    is_active: bool = True
    created_at: datetime = Field(default_factory=utc_now)


class ProductionLine(SQLModel, table=True):
    __tablename__ = "production_lines"
    id: Optional[int] = Field(default=None, primary_key=True)
    code: str = Field(index=True, unique=True, max_length=40)
    name: str = Field(max_length=150)
    plant_id: int = Field(foreign_key="plants.id", index=True)
    description: Optional[str] = Field(default=None, max_length=500)
    is_active: bool = True
    created_at: datetime = Field(default_factory=utc_now)


class Product(SQLModel, table=True):
    __tablename__ = "products"
    id: Optional[int] = Field(default=None, primary_key=True)
    code: str = Field(index=True, unique=True, max_length=40)
    name: str = Field(index=True, max_length=150)
    description: Optional[str] = Field(default=None, max_length=500)
    unit: str = Field(default="piece", max_length=30)
    is_active: bool = True
    created_at: datetime = Field(default_factory=utc_now)


class Material(SQLModel, table=True):
    __tablename__ = "materials"
    id: Optional[int] = Field(default=None, primary_key=True)
    code: str = Field(max_length=40, unique=True, index=True)
    name: str = Field(max_length=150, index=True)
    category: str = Field(max_length=100, index=True)
    unit: str = Field(max_length=30)
    available_quantity: float = Field(default=0, ge=0)
    minimum_stock_level: float = Field(default=0, ge=0)
    reorder_level: float = Field(default=0, ge=0)
    supplier_reference: Optional[str] = Field(default=None, max_length=100)
    status: MaterialStatus = Field(default=MaterialStatus.ACTIVE, index=True)
    created_at: datetime = Field(default_factory=utc_now)


class InventoryMovement(SQLModel, table=True):
    __tablename__ = "inventory_movements"
    id: Optional[int] = Field(default=None, primary_key=True)
    material_id: int = Field(foreign_key="materials.id", index=True)
    performed_by: int = Field(foreign_key="users.id", index=True)
    movement_type: MovementType = Field(index=True)
    quantity: float
    balance_after: float = Field(ge=0)
    reference: Optional[str] = Field(default=None, max_length=150)
    remarks: Optional[str] = Field(default=None, max_length=500)
    created_at: datetime = Field(default_factory=utc_now, index=True)


class BOMItem(SQLModel, table=True):
    __tablename__ = "bom_items"
    id: Optional[int] = Field(default=None, primary_key=True)
    product_id: int = Field(foreign_key="products.id", index=True)
    material_id: int = Field(foreign_key="materials.id", index=True)
    quantity_per_product: float = Field(gt=0)
    scrap_percent: float = Field(default=0, ge=0, le=100)
    created_at: datetime = Field(default_factory=utc_now)


class ProductionOrder(SQLModel, table=True):
    __tablename__ = "production_orders"
    id: Optional[int] = Field(default=None, primary_key=True)
    order_number: str = Field(unique=True, index=True, max_length=50)
    product_id: int = Field(foreign_key="products.id", index=True)
    production_line_id: int = Field(foreign_key="production_lines.id", index=True)
    planned_quantity: int = Field(gt=0)
    produced_quantity: int = Field(default=0, ge=0)
    status: ProductionOrderStatus = Field(default=ProductionOrderStatus.DRAFT, index=True)
    notes: Optional[str] = Field(default=None, max_length=500)
    created_by: int = Field(foreign_key="users.id")
    created_at: datetime = Field(default_factory=utc_now)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None


class QualityInspection(SQLModel, table=True):
    __tablename__ = "quality_inspections"
    id: Optional[int] = Field(default=None, primary_key=True)
    inspection_number: str = Field(unique=True, index=True, max_length=50)
    production_order_id: int = Field(foreign_key="production_orders.id", index=True)
    inspected_by: int = Field(foreign_key="users.id", index=True)
    quantity_inspected: int = Field(gt=0)
    quantity_passed: int = Field(ge=0)
    quantity_failed: int = Field(ge=0)
    decision: InspectionDecision = Field(index=True)
    notes: Optional[str] = Field(default=None, max_length=1000)
    created_at: datetime = Field(default_factory=utc_now)
