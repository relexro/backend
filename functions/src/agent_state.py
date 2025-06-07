"""
Agent State - Data models for the agent workflow state
"""
from typing import Dict, List, Any, Optional
from pydantic import BaseModel, Field
from datetime import datetime

class AgentState(BaseModel):
    """State for the agent workflow."""
    
    # User and case info
    user_id: str = Field(default="")
    case_id: str = Field(default="")
    organization_id: Optional[str] = None
    client_info: Dict[str, Any] = Field(default_factory=dict)
    case_details: Dict[str, Any] = Field(default_factory=dict)
    
    # Tracking node execution
    current_node: str = Field(default="")
    has_error: bool = Field(default=False)
    error_message: str = Field(default="")
    retry_count: Dict[str, int] = Field(default_factory=dict)
    errors: List[Dict[str, Any]] = Field(default_factory=list)
    completed_nodes: List[str] = Field(default_factory=list)
    
    # Results from each processing step
    tier: str = Field(default="basic")
    tier_details: Dict[str, Any] = Field(default_factory=dict)
    input_analysis: Dict[str, Any] = Field(default_factory=dict)
    research_results: Dict[str, Any] = Field(default_factory=dict)
    expert_consultation_results: Dict[str, Any] = Field(default_factory=dict)
    document_plan: Dict[str, Any] = Field(default_factory=dict)
    generated_documents: Dict[str, Any] = Field(default_factory=dict)
    final_review_results: Dict[str, Any] = Field(default_factory=dict)
    
    # Response data
    response_data: Dict[str, Any] = Field(default_factory=dict)
    
    # Session metadata
    start_time: str = Field(default_factory=lambda: datetime.now().isoformat())
    last_updated: str = Field(default_factory=lambda: datetime.now().isoformat())
    
    # Quota status
    quota_status: Dict[str, Any] = Field(default_factory=dict) 