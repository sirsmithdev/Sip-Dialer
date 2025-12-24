"""
Reporting schemas for analytics and scheduled reports.
"""
from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field

from app.models.report import ReportType, ReportFormat


# ============================================================================
# CALL ANALYTICS SCHEMAS
# ============================================================================

class CallDurationStats(BaseModel):
    """Call duration statistics."""
    average_ring_seconds: float = Field(..., description="Average ring duration")
    average_talk_seconds: float = Field(..., description="Average talk duration")
    average_total_seconds: float = Field(..., description="Average total call duration")
    median_talk_seconds: float = Field(..., description="Median talk duration")
    longest_call_seconds: int = Field(..., description="Longest call duration")
    shortest_call_seconds: int = Field(..., description="Shortest call duration")
    total_talk_time_hours: float = Field(..., description="Total talk time in hours")


class TimeDistribution(BaseModel):
    """Call distribution by time period."""
    hour: int = Field(..., ge=0, le=23, description="Hour of day (0-23)")
    calls_count: int = Field(..., description="Total calls in this hour")
    answered_count: int = Field(..., description="Answered calls in this hour")
    answer_rate: float = Field(..., description="Answer rate percentage")


class CallAnalyticsResponse(BaseModel):
    """Complete call analytics report."""
    campaign_id: Optional[str] = Field(None, description="Campaign ID (if filtered)")
    date_from: datetime = Field(..., description="Report start date")
    date_to: datetime = Field(..., description="Report end date")

    # Duration Analysis
    duration_stats: CallDurationStats

    # Time-based Performance
    calls_by_hour: List[TimeDistribution] = Field(..., description="Hourly call distribution")
    calls_by_day_of_week: List[Dict[str, Any]] = Field(..., description="Daily call distribution")
    peak_performance_hour: int = Field(..., description="Hour with best answer rate")

    # Outcome Breakdown
    outcomes: Dict[str, int] = Field(..., description="Call results distribution")
    amd_accuracy: Dict[str, int] = Field(..., description="AMD detection results")
    failed_reasons: Dict[str, int] = Field(..., description="Failure reasons distribution")


# ============================================================================
# CAMPAIGN PERFORMANCE SCHEMAS
# ============================================================================

class CampaignComparisonItem(BaseModel):
    """Single campaign in comparison report."""
    campaign_id: str
    campaign_name: str
    total_calls: int
    answer_rate: float = Field(..., description="Answer rate percentage")
    human_rate: float = Field(..., description="Human answer rate percentage")
    average_talk_time: float = Field(..., description="Average talk time in seconds")
    contacts_per_hour: float = Field(..., description="Calling efficiency")
    cost_per_contact: Optional[float] = Field(None, description="Cost per contact (if available)")


class CampaignComparisonResponse(BaseModel):
    """Multi-campaign comparison report."""
    campaigns: List[CampaignComparisonItem]
    organization_average_answer_rate: float = Field(..., description="Org-wide average")


class DailyStats(BaseModel):
    """Daily statistics for trend analysis."""
    date: str = Field(..., description="Date in YYYY-MM-DD format")
    calls: int
    answered: int
    answer_rate: float
    human_answers: int
    human_rate: float
    average_talk_time: float


class CampaignTrendsResponse(BaseModel):
    """Campaign performance trends over time."""
    campaign_id: str
    campaign_name: str
    daily_stats: List[DailyStats] = Field(..., description="Daily breakdown")
    weekly_stats: List[Dict[str, Any]] = Field(..., description="Weekly aggregates")


# ============================================================================
# CONTACT LIST QUALITY SCHEMAS
# ============================================================================

class ListPerformance(BaseModel):
    """Performance metrics for a contact list."""
    list_id: str
    list_name: str
    answer_rate: float
    total_calls: int


class ContactListQualityResponse(BaseModel):
    """Contact list data quality analysis."""
    list_id: Optional[str] = Field(None, description="Specific list ID (if filtered)")
    list_name: Optional[str] = Field(None, description="List name (if filtered)")
    total_contacts: int
    valid_contacts: int
    invalid_contacts: int
    invalid_rate: float = Field(..., description="Percentage of invalid numbers")
    dnc_hits: int = Field(..., description="Contacts on DNC list")
    dnc_rate: float = Field(..., description="DNC percentage")
    answer_rate_by_list: float = Field(..., description="Answer rate for this list")
    best_performing_lists: List[ListPerformance] = Field(..., description="Top 5 performing lists")


# ============================================================================
# REAL-TIME MONITORING SCHEMAS
# ============================================================================

class RealTimeMetrics(BaseModel):
    """Live campaign metrics."""
    active_calls: int = Field(..., description="Currently active calls")
    queued_calls: int = Field(..., description="Calls waiting in queue")
    calls_per_minute: float = Field(..., description="Current call rate")
    current_answer_rate: float = Field(..., description="Answer rate for last hour")
    line_utilization_percent: float = Field(..., description="Line usage percentage")
    active_campaigns_count: int = Field(..., description="Number of running campaigns")


# ============================================================================
# IVR/SURVEY ANALYTICS SCHEMAS
# ============================================================================

class QuestionResponse(BaseModel):
    """Response distribution for a survey question."""
    question_id: str
    question_text: str
    response_count: int
    responses: Dict[str, int] = Field(..., description="Response value -> count")


class DropOffPoint(BaseModel):
    """Points where users drop off from survey."""
    step: int
    step_name: str
    drop_off_count: int
    drop_off_rate: float


class IVRSurveyAnalyticsResponse(BaseModel):
    """IVR and survey response analytics."""
    survey_id: Optional[str] = Field(None, description="Survey ID (if filtered)")
    survey_name: Optional[str] = Field(None, description="Survey name")
    total_responses: int
    completion_rate: float = Field(..., description="Percentage of completed surveys")
    average_duration_seconds: float = Field(..., description="Average survey duration")
    questions_answered_avg: float = Field(..., description="Average questions answered")
    responses_by_question: List[QuestionResponse] = Field(..., description="Per-question breakdown")
    drop_off_points: List[DropOffPoint] = Field(..., description="Where users drop off")


# ============================================================================
# COMPLIANCE REPORT SCHEMAS
# ============================================================================

class ViolationDetail(BaseModel):
    """Details of a compliance violation."""
    violation_type: str
    timestamp: datetime
    campaign_id: str
    campaign_name: str
    contact_phone: str
    details: str


class ComplianceReportResponse(BaseModel):
    """TCPA and quality compliance report."""
    organization_id: str
    date_from: datetime
    date_to: datetime

    # TCPA Compliance
    calls_outside_hours: int = Field(..., description="Calls outside permitted hours")
    violations_count: int = Field(..., description="Total TCPA violations")
    violation_details: List[ViolationDetail] = Field(..., description="Detailed violations")

    # DNC Compliance
    dnc_list_checks: int = Field(..., description="Total DNC checks performed")
    dnc_violations: int = Field(..., description="Calls to DNC numbers")

    # Call Quality
    total_calls: int
    successful_recordings: int = Field(..., description="Calls with recordings")
    recording_rate: float = Field(..., description="Percentage with recordings")
    average_quality_score: Optional[float] = Field(None, description="Avg quality score")


# ============================================================================
# REPORT SCHEDULE SCHEMAS
# ============================================================================

class ReportScheduleCreate(BaseModel):
    """Create a new report schedule."""
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = Field(None, max_length=500)
    report_type: ReportType
    format: ReportFormat
    schedule_cron: str = Field(..., description="Cron expression")
    recipients_json: List[str] = Field(..., description="Email recipients")
    filters_json: Dict[str, Any] = Field(default_factory=dict)
    is_active: bool = Field(default=True)


class ReportScheduleUpdate(BaseModel):
    """Update an existing report schedule."""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    schedule_cron: Optional[str] = None
    recipients_json: Optional[List[str]] = None
    filters_json: Optional[Dict[str, Any]] = None
    is_active: Optional[bool] = None


class ReportScheduleResponse(BaseModel):
    """Report schedule details."""
    id: str
    organization_id: str
    name: str
    description: Optional[str]
    report_type: ReportType
    format: ReportFormat
    schedule_cron: str
    recipients_json: List[str]
    filters_json: Dict[str, Any]
    is_active: bool
    last_run_at: Optional[datetime]
    next_run_at: Optional[datetime]
    last_execution_status: Optional[str]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# ============================================================================
# REPORT EXECUTION SCHEMAS
# ============================================================================

class ReportExecutionResponse(BaseModel):
    """Report execution details."""
    id: str
    report_schedule_id: Optional[str]
    organization_id: str
    report_type: ReportType
    format: ReportFormat
    status: str
    file_path: Optional[str]
    file_size_bytes: Optional[int]
    execution_time_seconds: Optional[float]
    records_count: Optional[int]
    error_message: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True


# ============================================================================
# EXPORT SCHEMAS
# ============================================================================

class ExportRequest(BaseModel):
    """Request to export a report."""
    report_type: ReportType
    format: ReportFormat
    filters: Dict[str, Any] = Field(default_factory=dict)


class ExportStatusResponse(BaseModel):
    """Export task status."""
    task_id: str
    status: str = Field(..., description="PENDING, RUNNING, COMPLETED, FAILED")
    progress: Optional[float] = Field(None, description="Progress percentage")
    result: Optional[Dict[str, Any]] = Field(None, description="Result data")
    error: Optional[str] = None


class ExportDownloadResponse(BaseModel):
    """Export download information."""
    download_url: str = Field(..., description="Presigned download URL")
    expires_in_seconds: int = Field(..., description="URL expiration time")
    file_size_bytes: int
    file_name: str
