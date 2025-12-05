from pydantic import BaseModel, Field
from typing import Optional
from enum import Enum


class PlanStatus(str, Enum):
    """Valid status values for coaching recommendations."""
    COMPLETED = "completed"
    SKIPPED = "skipped"
    PARTIAL = "partial"


class UpdatePlanStatusRequest(BaseModel):
    """Request to update coaching recommendation status."""

    status: PlanStatus = Field(
        ...,
        description="New status for the plan: completed, skipped, or partial"
    )
    notes: Optional[str] = Field(
        None,
        max_length=500,
        description="Optional notes about the status update (e.g., 'Did 20 min instead of 30 min')"
    )


class UpdatePlanStatusResponse(BaseModel):
    """Response from updating plan status."""

    success: bool
    message: str
    recommendation_id: str
    new_status: str
