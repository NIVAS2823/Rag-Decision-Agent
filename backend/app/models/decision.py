"""
Decision Models
===============
Pydantic models for AI-generated decision data.
"""

from datetime import datetime
from typing import Optional, List, Dict, Any
from enum import Enum

from pydantic import BaseModel, Field
from bson import ObjectId

from app.models.user import PyObjectId


# ============================================================================
# ENUMS
# ============================================================================

class DecisionStatus(str, Enum):
    """Decision processing status"""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class ConfidenceLevel(str, Enum):
    """Confidence level categories"""
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


# ============================================================================
# NESTED MODELS
# ============================================================================

class Citation(BaseModel):
    """
    Source citation for decision claims
    """
    source_id: Optional[str] = Field(default=None, description="Document ID if internal source")
    source_type: str = Field(..., description="Type: document, web, database")
    title: str = Field(..., description="Source title")
    url: Optional[str] = Field(default=None, description="URL if web source")
    excerpt: str = Field(..., description="Relevant excerpt from source")
    page_number: Optional[int] = Field(default=None, description="Page number if applicable")
    relevance_score: Optional[float] = Field(default=None, ge=0.0, le=1.0, description="Relevance score")
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "source_type": "document",
                "title": "Q4 2024 Financial Report",
                "excerpt": "Revenue increased by 23% year-over-year",
                "page_number": 5,
                "relevance_score": 0.92
            }
        }
    }


class VerificationResult(BaseModel):
    """
    Fact verification results
    """
    claim: str = Field(..., description="The claim being verified")
    verified: bool = Field(..., description="Whether claim was verified")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Verification confidence")
    sources: List[str] = Field(default_factory=list, description="Sources that support/refute claim")
    notes: Optional[str] = Field(default=None, description="Additional verification notes")
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "claim": "Market share increased by 15%",
                "verified": True,
                "confidence": 0.88,
                "sources": ["Industry Report 2024", "Internal Analytics"],
                "notes": "Verified against Q4 data"
            }
        }
    }


class ConfidenceScore(BaseModel):
    """
    Detailed confidence scoring
    """
    overall_score: float = Field(..., ge=0.0, le=1.0, description="Overall confidence score")
    level: ConfidenceLevel = Field(..., description="Confidence level category")
    factors: Dict[str, float] = Field(
        default_factory=dict,
        description="Individual confidence factors (data_quality, source_reliability, etc.)"
    )
    reasoning: str = Field(..., description="Explanation of confidence assessment")
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "overall_score": 0.85,
                "level": "high",
                "factors": {
                    "data_quality": 0.90,
                    "source_reliability": 0.85,
                    "claim_verification": 0.80
                },
                "reasoning": "High confidence based on multiple verified sources"
            }
        }
    }


class DecisionOutput(BaseModel):
    """
    Structured decision output from AI
    """
    recommendation: str = Field(..., description="Primary recommendation")
    reasoning: str = Field(..., description="Detailed reasoning for the decision")
    pros: List[str] = Field(default_factory=list, description="Advantages/benefits")
    cons: List[str] = Field(default_factory=list, description="Disadvantages/risks")
    risks: List[str] = Field(default_factory=list, description="Identified risks")
    alternatives: List[str] = Field(default_factory=list, description="Alternative options")
    next_steps: List[str] = Field(default_factory=list, description="Recommended next steps")
    timeframe: Optional[str] = Field(default=None, description="Recommended timeframe for decision")
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "recommendation": "Proceed with market expansion to Asia-Pacific",
                "reasoning": "Strong market demand and favorable economic conditions",
                "pros": ["Growing market", "Low competition", "High margins"],
                "cons": ["Initial investment required", "Currency risk"],
                "risks": ["Regulatory changes", "Economic downturn"],
                "alternatives": ["European expansion", "Digital-first strategy"],
                "next_steps": ["Conduct market research", "Hire local team"],
                "timeframe": "6-12 months"
            }
        }
    }


class RetrievalContext(BaseModel):
    """
    RAG retrieval context information
    """
    query_embedding_model: str = Field(..., description="Embedding model used")
    top_k_documents: int = Field(..., description="Number of documents retrieved")
    retrieval_method: str = Field(..., description="Retrieval method: hybrid, vector, keyword")
    reranked: bool = Field(default=False, description="Whether results were re-ranked")
    avg_similarity_score: Optional[float] = Field(default=None, description="Average similarity score")
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "query_embedding_model": "text-embedding-3-small",
                "top_k_documents": 10,
                "retrieval_method": "hybrid",
                "reranked": True,
                "avg_similarity_score": 0.78
            }
        }
    }


# ============================================================================
# DATABASE MODEL
# ============================================================================

class DecisionInDB(BaseModel):
    """
    Decision model as stored in database
    """
    id: Optional[PyObjectId] = Field(default=None, alias="_id")
    user_id: str = Field(..., description="ID of user who requested decision")
    
    # Query information
    query: str = Field(..., description="Original decision query")
    context: Optional[str] = Field(default=None, description="Additional context provided")
    
    # Decision output
    decision: DecisionOutput = Field(..., description="Structured decision output")
    
    # Citations and sources
    citations: List[Citation] = Field(default_factory=list, description="Source citations")
    
    # Verification
    verification_results: List[VerificationResult] = Field(
        default_factory=list,
        description="Fact verification results"
    )
    
    # Confidence
    confidence: ConfidenceScore = Field(..., description="Confidence scoring")
    
    # Retrieval information
    retrieval_context: Optional[RetrievalContext] = Field(
        default=None,
        description="RAG retrieval context"
    )
    
    # Agent execution trace
    agent_trace_id: Optional[str] = Field(
        default=None,
        description="LangSmith trace ID for debugging"
    )
    
    # Processing information
    status: DecisionStatus = Field(default=DecisionStatus.PENDING, description="Processing status")
    processing_time_ms: Optional[float] = Field(default=None, description="Total processing time")
    llm_model_used: Optional[str] = Field(default=None, description="LLM model used")
    total_tokens: Optional[int] = Field(default=None, description="Total tokens used")
    
    # Error handling
    error_message: Optional[str] = Field(default=None, description="Error message if failed")
    
    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = Field(default=None)
    
    # Metadata
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")
    
    model_config = {
        "populate_by_name": True,
        "arbitrary_types_allowed": True,
        "json_encoders": {ObjectId: str},
    }


# ============================================================================
# REQUEST MODELS
# ============================================================================

class DecisionCreate(BaseModel):
    """
    Decision creation request
    """
    query: str = Field(
        ...,
        min_length=10,
        max_length=2000,
        description="Decision query/question"
    )
    context: Optional[str] = Field(
        default=None,
        max_length=5000,
        description="Additional context for the decision"
    )
    document_ids: Optional[List[str]] = Field(
        default=None,
        description="Specific document IDs to consider"
    )
    enable_web_search: Optional[bool] = Field(
        default=None,
        description="Enable web search (overrides config)"
    )
    enable_verification: Optional[bool] = Field(
        default=None,
        description="Enable fact verification (overrides config)"
    )
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "query": "Should we expand our product line to include AI-powered tools?",
                "context": "We currently serve 50K users and have $2M in revenue",
                "enable_web_search": True,
                "enable_verification": True
            }
        }
    }


# ============================================================================
# RESPONSE MODELS
# ============================================================================

class Decision(BaseModel):
    """
    Decision response model
    """
    id: str = Field(..., description="Decision ID")
    user_id: str = Field(..., description="User ID")
    query: str = Field(..., description="Original query")
    decision: DecisionOutput = Field(..., description="Structured decision")
    citations: List[Citation] = Field(default_factory=list)
    verification_results: List[VerificationResult] = Field(default_factory=list)
    confidence: ConfidenceScore = Field(..., description="Confidence score")
    status: DecisionStatus = Field(..., description="Processing status")
    processing_time_ms: Optional[float] = Field(default=None)
    created_at: datetime = Field(...)
    completed_at: Optional[datetime] = Field(default=None)
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "id": "507f1f77bcf86cd799439011",
                "user_id": "507f1f77bcf86cd799439012",
                "query": "Should we expand to Asia-Pacific?",
                "decision": {},
                "citations": [],
                "confidence": {},
                "status": "completed",
                "processing_time_ms": 3542.5,
                "created_at": "2025-01-22T12:00:00Z",
                "completed_at": "2025-01-22T12:00:04Z"
            }
        }
    }
    
    @classmethod
    def from_db(cls, decision_db: DecisionInDB) -> "Decision":
        """
        Convert database model to response model
        
        Args:
            decision_db: Decision from database
            
        Returns:
            Decision: Decision response model
        """
        return cls(
            id=str(decision_db.id),
            user_id=decision_db.user_id,
            query=decision_db.query,
            decision=decision_db.decision,
            citations=decision_db.citations,
            verification_results=decision_db.verification_results,
            confidence=decision_db.confidence,
            status=decision_db.status,
            processing_time_ms=decision_db.processing_time_ms,
            created_at=decision_db.created_at,
            completed_at=decision_db.completed_at,
        )


class DecisionList(BaseModel):
    """
    List of decisions response
    """
    decisions: List[Decision] = Field(..., description="List of decisions")
    total: int = Field(..., description="Total number of decisions")
    page: int = Field(default=1, description="Current page")
    page_size: int = Field(default=10, description="Page size")
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "decisions": [],
                "total": 25,
                "page": 1,
                "page_size": 10
            }
        }
    }


class DecisionStats(BaseModel):
    """
    Decision statistics for a user
    """
    total_decisions: int = Field(..., description="Total decisions made")
    completed_decisions: int = Field(..., description="Completed decisions")
    pending_decisions: int = Field(..., description="Pending decisions")
    failed_decisions: int = Field(..., description="Failed decisions")
    avg_processing_time_ms: Optional[float] = Field(default=None)
    avg_confidence_score: Optional[float] = Field(default=None)
    total_tokens_used: Optional[int] = Field(default=None)