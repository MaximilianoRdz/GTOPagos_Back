"""
GTOPagos Agent Schemas (Pydantic v2)
Contratos tipados para validación estricta de entradas y salidas en SDD y MCP.
"""
from pydantic import BaseModel, Field, field_validator
from typing import List, Optional, Literal
from decimal import Decimal
from datetime import date


# ==============================================================================
# 1. SCHEMAS: SKILL MESES SIN INTERESES (MSI)
# ==============================================================================
class MSICalculatorInput(BaseModel):
    total_amount: Decimal = Field(gt=0, description="Monto total de la compra en pesos")
    total_installments: int = Field(ge=2, le=72, description="Número total de cuotas pactadas (ej: 3, 6, 12, 18, 24)")
    current_installment: int = Field(default=1, ge=1, description="Número de cuota que se está evaluando o pagando")

    @field_validator('current_installment')
    @classmethod
    def validate_current_installment(cls, v, info):
        if 'total_installments' in info.data and v > info.data['total_installments']:
            raise ValueError("La cuota actual no puede ser mayor al número total de cuotas.")
        return v


class MSIInstallmentSchedule(BaseModel):
    installment_number: int
    amount: Decimal
    status: Literal["PAGADO", "PENDIENTE"]


class MSICalculatorOutput(BaseModel):
    total_amount: Decimal
    total_installments: int
    current_installment: int
    monthly_installment: Decimal
    biweekly_installment: Decimal
    amount_paid_so_far: Decimal
    remaining_balance: Decimal
    remaining_installments: int
    is_fully_paid: bool
    schedule: List[MSIInstallmentSchedule]


# ==============================================================================
# 2. SCHEMAS: SKILL DE FLUJO DE CAJA (CASHFLOW FORECAST)
# ==============================================================================
class PendingObligation(BaseModel):
    description: str
    amount: Decimal = Field(gt=0)
    due_date: date
    category: Optional[str] = "General"
    is_paid: bool = False


class CashflowForecastInput(BaseModel):
    salary: Decimal = Field(gt=0, description="Ingreso o salario esperado para la quincena/mes")
    cutoff_day: Literal[15, 30] = Field(default=15, description="Día de corte de la quincena a evaluar (15 o 30)")
    obligations: List[PendingObligation] = Field(default_factory=list, description="Lista de pagos o gastos del periodo")


class CashflowForecastOutput(BaseModel):
    cutoff_day: int
    total_income: Decimal
    total_committed: Decimal
    available_margin: Decimal
    compromised_percentage: Decimal
    risk_level: Literal["BAJO", "MODERADO", "ALTO", "CRÍTICO"]
    risk_alert: Optional[str] = None
    pending_items_count: int


# ==============================================================================
# 3. SCHEMAS: SKILL DE PRIORIDAD DE VENCIMIENTOS (DUE DATE PRIORITY)
# ==============================================================================
class DueDateItem(BaseModel):
    id: Optional[int] = None
    concept: str
    amount: Decimal = Field(gt=0)
    due_date: date
    is_paid: bool = False


class PrioritizedObligation(BaseModel):
    id: Optional[int] = None
    concept: str
    amount: Decimal
    due_date: date
    days_left: int
    priority: Literal["CRÍTICO", "URGENTE", "PRÓXIMO", "HOLGADO", "VENCIDO"]
    color_code: str  # Hex para la interfaz gráfica


class DueDatePriorityInput(BaseModel):
    reference_date: date = Field(default_factory=date.today)
    items: List[DueDateItem]


class DueDatePriorityOutput(BaseModel):
    reference_date: date
    critical_count: int
    total_pending_amount: Decimal
    prioritized_list: List[PrioritizedObligation]


# ==============================================================================
# 4. SCHEMAS: SKILL DE CATEGORIZACIÓN INTELIGENTE (SMART CATEGORIZER)
# ==============================================================================
class CategorizerInput(BaseModel):
    description: str = Field(min_length=2, description="Texto de la transacción, concepto o estado de cuenta")
    amount: Optional[Decimal] = None


class CategorizerOutput(BaseModel):
    original_text: str
    suggested_category: str
    behavior: Literal["EXPENSE", "INCOME", "TRANSFER"]
    confidence: Decimal = Field(ge=0, le=1)
    matched_keyword: Optional[str] = None


# ==============================================================================
# 5. SCHEMAS: MCP TOOLS MUTATION & INTEGRATION
# ==============================================================================
class CreateRecordToolInput(BaseModel):
    dashboard_id: int
    record_type: Literal["INCOME", "EXPENSE", "TRANSFER"]
    amount: Decimal = Field(gt=0, description="Monto estrictamente positivo con 2 decimales")
    description: str = Field(min_length=2)
    record_date: date = Field(default_factory=date.today)
    category_id: Optional[int] = None
    payment_method_id: Optional[int] = None
    payment_status_code: Optional[str] = "PENDING"
    is_recurrent: bool = False
    total_installments: Optional[int] = None
    current_installment: Optional[int] = None


class UpdateRecordStatusToolInput(BaseModel):
    record_id: int
    target_status: Literal["PAGADO", "PAID", "CANCELADO", "PENDIENTE"]


class AgentActionResponse(BaseModel):
    success: bool
    thought: str
    action_type: Literal["READ_ONLY", "MUTATION", "CALCULATION", "ALERT"]
    data: dict
    user_message: str
