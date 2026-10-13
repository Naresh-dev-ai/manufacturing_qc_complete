from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict, Field as PField
from app.models import (
    UserRole, MaterialStatus, ProductionOrderStatus, InspectionDecision
)


class UserCreate(BaseModel):
    username: str = PField(min_length=3, max_length=80)
    full_name: str = PField(min_length=2, max_length=150)
    password: str = PField(min_length=8, max_length=128)
    role: UserRole = UserRole.WORKER


class UserRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    username: str
    full_name: str
    role: UserRole
    is_active: bool
    created_at: datetime


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class PlantCreate(BaseModel):
    code: str = PField(min_length=2, max_length=40)
    name: str = PField(min_length=2, max_length=150)
    address: Optional[str] = PField(default=None, max_length=300)


class PlantRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    code: str
    name: str
    address: Optional[str]
    is_active: bool
    created_at: datetime


class ProductionLineCreate(BaseModel):
    code: str = PField(min_length=2, max_length=40)
    name: str = PField(min_length=2, max_length=150)
    plant_id: int
    description: Optional[str] = PField(default=None, max_length=500)


class ProductionLineRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    code: str
    name: str
    plant_id: int
    description: Optional[str]
    is_active: bool
    created_at: datetime


class ProductCreate(BaseModel):
    code: str = PField(min_length=2, max_length=40)
    name: str = PField(min_length=2, max_length=150)
    description: Optional[str] = PField(default=None, max_length=500)
    unit: str = PField(default="piece", min_length=1, max_length=30)


class ProductRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    code: str
    name: str
    description: Optional[str]
    unit: str
    is_active: bool
    created_at: datetime


class MaterialCreate(BaseModel):
    code: str = PField(min_length=2, max_length=40)
    name: str = PField(min_length=2, max_length=150)
    category: str = PField(min_length=2, max_length=100)
    unit: str = PField(min_length=1, max_length=30)
    minimum_stock_level: float = PField(default=0, ge=0)
    reorder_level: float = PField(default=0, ge=0)
    supplier_reference: Optional[str] = PField(default=None, max_length=100)


class MaterialRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    code: str
    name: str
    category: str
    unit: str
    available_quantity: float
    minimum_stock_level: float
    reorder_level: float
    supplier_reference: Optional[str]
    status: MaterialStatus
    created_at: datetime


class MaterialStatusUpdate(BaseModel):
    status: MaterialStatus


class StockMovementRequest(BaseModel):
    quantity: float = PField(gt=0)
    reference: Optional[str] = PField(default=None, max_length=150)
    remarks: Optional[str] = PField(default=None, max_length=500)


class StockAdjustmentRequest(BaseModel):
    quantity_change: float
    reference: Optional[str] = PField(default=None, max_length=150)
    remarks: str = PField(min_length=3, max_length=500)


class InventoryMovementRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    material_id: int
    performed_by: int
    movement_type: str
    quantity: float
    balance_after: float
    reference: Optional[str]
    remarks: Optional[str]
    created_at: datetime


class BOMItemCreate(BaseModel):
    material_id: int
    quantity_per_product: float = PField(gt=0)
    scrap_percent: float = PField(default=0, ge=0, le=100)


class BOMItemRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    product_id: int
    material_id: int
    quantity_per_product: float
    scrap_percent: float
    created_at: datetime


class MaterialRequirement(BaseModel):
    material_id: int
    material_code: str
    material_name: str
    unit: str
    quantity_per_product: float
    scrap_percent: float
    required_quantity: float
    available_quantity: float
    sufficient: bool


class ProductionOrderCreate(BaseModel):
    order_number: str = PField(min_length=3, max_length=50)
    product_id: int
    production_line_id: int
    planned_quantity: int = PField(gt=0)
    notes: Optional[str] = PField(default=None, max_length=500)


class ProductionOrderRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    order_number: str
    product_id: int
    production_line_id: int
    planned_quantity: int
    produced_quantity: int
    status: ProductionOrderStatus
    notes: Optional[str]
    created_by: int
    created_at: datetime
    started_at: Optional[datetime]
    completed_at: Optional[datetime]


class ProductionCompletion(BaseModel):
    produced_quantity: int = PField(gt=0)


class QualityInspectionCreate(BaseModel):
    inspection_number: str = PField(min_length=3, max_length=50)
    production_order_id: int
    quantity_inspected: int = PField(gt=0)
    quantity_passed: int = PField(ge=0)
    quantity_failed: int = PField(ge=0)
    decision: InspectionDecision
    notes: Optional[str] = PField(default=None, max_length=1000)


class QualityInspectionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    inspection_number: str
    production_order_id: int
    inspected_by: int
    quantity_inspected: int
    quantity_passed: int
    quantity_failed: int
    decision: InspectionDecision
    notes: Optional[str]
    created_at: datetime
