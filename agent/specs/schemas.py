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


# ==============================================================================
# 6. SCHEMAS: SKILL DE AUDITORÍA INTEGRAL DEL SISTEMA (SYSTEM AUDIT 360°)
# ==============================================================================
class AuditRecordItem(BaseModel):
    id: Optional[int] = None
    description: str = ""
    amount: Decimal = Field(gt=0)
    behavior: Literal["INCOME", "EXPENSE", "TRANSFER"]
    category_name: str = "Otros"
    record_date: date
    is_recurrent: bool = False
    total_installments: Optional[int] = None
    current_installment: Optional[int] = None
    payment_status: str = "PAGADO"


class AuditGoalItem(BaseModel):
    id: Optional[int] = None
    name: str
    target_amount: Decimal = Field(gt=0)
    saved_amount: Decimal = Field(ge=0, default=Decimal('0.00'))
    target_date: Optional[date] = None


class SystemAuditInput(BaseModel):
    user_name: str = "Usuario"
    salary: Decimal = Field(default=Decimal('0.00'), ge=0)
    records: List[AuditRecordItem] = Field(default_factory=list)
    goals: List[AuditGoalItem] = Field(default_factory=list)


class CategoryBreakdownItem(BaseModel):
    category: str
    total_amount: Decimal
    percentage_of_expenses: Decimal
    count: int


class GoalFeasibilityItem(BaseModel):
    name: str
    saved_amount: Decimal
    target_amount: Decimal
    progress_percentage: Decimal
    remaining_amount: Decimal
    monthly_required: Decimal
    is_viable: bool
    status: Literal["LOGRADA", "VIABLE", "EN RIESGO"]
    message: str


class AuditRecommendation(BaseModel):
    priority: Literal["ALTA", "MEDIA", "OPTIMIZACIÓN"]
    title: str
    detail: str
    action_type: str


class SystemAuditOutput(BaseModel):
    health_score: int  # 0 to 100
    health_status: Literal["EXCELENTE", "SALUDABLE", "MEJORABLE", "CRÍTICO"]
    total_income: Decimal
    total_expenses: Decimal
    net_savings: Decimal
    savings_rate: Decimal  # %
    debt_burden_rate: Decimal  # % de gastos en deudas o compras a cuotas
    monthly_fixed_commitments: Decimal
    top_categories: List[CategoryBreakdownItem]
    goals_feasibility: List[GoalFeasibilityItem]
    recommendations: List[AuditRecommendation]
    summary_text: str


class AgentActionResponse(BaseModel):
    success: bool
    thought: str
    action_type: Literal["READ_ONLY", "MUTATION", "CALCULATION", "ALERT"]
    data: dict
    user_message: str

