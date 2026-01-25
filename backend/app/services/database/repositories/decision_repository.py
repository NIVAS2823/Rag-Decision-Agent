"""
Decision Repository
===================
Database operations for AI-generated decisions.
"""

from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta

from bson import ObjectId
from pymongo import DESCENDING

from app.models.decision import (
    DecisionInDB,
    DecisionCreate,
    Decision,
    DecisionStatus,
    DecisionStats,
)
from app.services.database import db_client
from app.core.logging_config import get_logger


logger = get_logger(__name__)


class DecisionRepository:
    """
    Decision repository for database operations
    """
    @property
    def collection(self):
        return db_client.get_decisions_collection()
    
    def __init__(self):
        """Initialize repository"""
        pass
    
    async def create(self, user_id: str, decision_data: DecisionCreate) -> DecisionInDB:
        """
        Create a new decision request
        
        Args:
            user_id: ID of user requesting decision
            decision_data: Decision creation data
            
        Returns:
            DecisionInDB: Created decision (in pending state)
        """
        # Create decision document (initially in pending state)
        decision_dict = {
            "user_id": user_id,
            "query": decision_data.query,
            "context": decision_data.context,
            "status": DecisionStatus.PENDING,
            "decision": None,  # Will be populated when processing completes
            "citations": [],
            "verification_results": [],
            "confidence": None,
            "retrieval_context": None,
            "agent_trace_id": None,
            "processing_time_ms": None,
            "llm_model_used": None,
            "total_tokens": None,
            "error_message": None,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
            "completed_at": None,
            "metadata": {
                "document_ids": decision_data.document_ids or [],
                "enable_web_search": decision_data.enable_web_search,
                "enable_verification": decision_data.enable_verification,
            }
        }
        
        result = await self.collection.insert_one(decision_dict)
        decision_dict["_id"] = result.inserted_id
        
        logger.info(
            f"Created decision request for user: {user_id}",
            extra={
                "decision_id": str(result.inserted_id),
                "query_preview": decision_data.query[:50]
            }
        )
        
        return DecisionInDB(**decision_dict)
    
    async def get_by_id(self, decision_id: str) -> Optional[DecisionInDB]:
        """
        Get decision by ID
        
        Args:
            decision_id: Decision ID
            
        Returns:
            Optional[DecisionInDB]: Decision if found, None otherwise
        """
        if not ObjectId.is_valid(decision_id):
            return None
        
        decision_dict = await self.collection.find_one({"_id": ObjectId(decision_id)})
        
        if decision_dict:
            return DecisionInDB(**decision_dict)
        return None
    
    async def get_by_user(
        self,
        user_id: str,
        skip: int = 0,
        limit: int = 10,
        status: Optional[DecisionStatus] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> List[DecisionInDB]:
        """
        Get decisions for a specific user
        
        Args:
            user_id: User ID
            skip: Number of decisions to skip
            limit: Maximum number of decisions to return
            status: Filter by status
            start_date: Filter decisions after this date
            end_date: Filter decisions before this date
            
        Returns:
            List[DecisionInDB]: List of decisions
        """
        # Build query
        query = {"user_id": user_id}
        
        if status:
            query["status"] = status
        
        if start_date or end_date:
            query["created_at"] = {}
            if start_date:
                query["created_at"]["$gte"] = start_date
            if end_date:
                query["created_at"]["$lte"] = end_date
        
        # Query with sorting (most recent first)
        cursor = self.collection.find(query).skip(skip).limit(limit).sort("created_at", DESCENDING)
        
        decisions = []
        async for decision_dict in cursor:
            decisions.append(DecisionInDB(**decision_dict))
        
        return decisions
    
    async def count_by_user(
        self,
        user_id: str,
        status: Optional[DecisionStatus] = None
    ) -> int:
        """
        Count decisions for a user
        
        Args:
            user_id: User ID
            status: Filter by status
            
        Returns:
            int: Number of decisions
        """
        query = {"user_id": user_id}
        if status:
            query["status"] = status
        
        return await self.collection.count_documents(query)
    
    async def update_status(
        self,
        decision_id: str,
        status: DecisionStatus,
        error_message: Optional[str] = None
    ) -> Optional[DecisionInDB]:
        """
        Update decision status
        
        Args:
            decision_id: Decision ID
            status: New status
            error_message: Error message if failed
            
        Returns:
            Optional[DecisionInDB]: Updated decision if found
        """
        if not ObjectId.is_valid(decision_id):
            return None
        
        update_dict = {
            "status": status,
            "updated_at": datetime.utcnow()
        }
        
        if status == DecisionStatus.COMPLETED or status == DecisionStatus.FAILED:
            update_dict["completed_at"] = datetime.utcnow()
        
        if error_message:
            update_dict["error_message"] = error_message
        
        result = await self.collection.find_one_and_update(
            {"_id": ObjectId(decision_id)},
            {"$set": update_dict},
            return_document=True
        )
        
        if result:
            logger.info(
                f"Updated decision status: {status}",
                extra={"decision_id": decision_id}
            )
            return DecisionInDB(**result)
        
        return None
    
    async def update_with_result(
        self,
        decision_id: str,
        decision_output: Dict[str, Any],
        citations: List[Dict[str, Any]],
        confidence: Dict[str, Any],
        verification_results: Optional[List[Dict[str, Any]]] = None,
        retrieval_context: Optional[Dict[str, Any]] = None,
        processing_time_ms: Optional[float] = None,
        llm_model: Optional[str] = None,
        total_tokens: Optional[int] = None,
        agent_trace_id: Optional[str] = None
    ) -> Optional[DecisionInDB]:
        """
        Update decision with AI-generated results
        
        Args:
            decision_id: Decision ID
            decision_output: Decision output data
            citations: Source citations
            confidence: Confidence score
            verification_results: Verification results
            retrieval_context: RAG retrieval context
            processing_time_ms: Processing time in milliseconds
            llm_model: LLM model used
            total_tokens: Total tokens used
            agent_trace_id: LangSmith trace ID
            
        Returns:
            Optional[DecisionInDB]: Updated decision
        """
        if not ObjectId.is_valid(decision_id):
            return None
        
        update_dict = {
            "decision": decision_output,
            "citations": citations,
            "confidence": confidence,
            "status": DecisionStatus.COMPLETED,
            "updated_at": datetime.utcnow(),
            "completed_at": datetime.utcnow()
        }
        
        if verification_results:
            update_dict["verification_results"] = verification_results
        if retrieval_context:
            update_dict["retrieval_context"] = retrieval_context
        if processing_time_ms is not None:
            update_dict["processing_time_ms"] = processing_time_ms
        if llm_model:
            update_dict["llm_model_used"] = llm_model
        if total_tokens is not None:
            update_dict["total_tokens"] = total_tokens
        if agent_trace_id:
            update_dict["agent_trace_id"] = agent_trace_id
        
        result = await self.collection.find_one_and_update(
            {"_id": ObjectId(decision_id)},
            {"$set": update_dict},
            return_document=True
        )
        
        if result:
            logger.info(
                f"Decision completed successfully",
                extra={
                    "decision_id": decision_id,
                    "processing_time_ms": processing_time_ms
                }
            )
            return DecisionInDB(**result)
        
        return None
    
    async def delete(self, decision_id: str) -> bool:
        """
        Delete decision
        
        Args:
            decision_id: Decision ID
            
        Returns:
            bool: True if deleted, False if not found
        """
        if not ObjectId.is_valid(decision_id):
            return False
        
        result = await self.collection.delete_one({"_id": ObjectId(decision_id)})
        
        if result.deleted_count > 0:
            logger.info(f"Deleted decision: {decision_id}")
            return True
        
        return False
    
    async def search(
        self,
        user_id: str,
        search_query: str,
        skip: int = 0,
        limit: int = 10
    ) -> List[DecisionInDB]:
        """
        Search decisions by text
        
        Args:
            user_id: User ID
            search_query: Search query
            skip: Number of results to skip
            limit: Maximum number of results
            
        Returns:
            List[DecisionInDB]: Matching decisions
        """
        cursor = self.collection.find(
            {
                "user_id": user_id,
                "$text": {"$search": search_query}
            },
            {"score": {"$meta": "textScore"}}
        ).sort([("score", {"$meta": "textScore"})]).skip(skip).limit(limit)
        
        decisions = []
        async for decision_dict in cursor:
            decisions.append(DecisionInDB(**decision_dict))
        
        return decisions
    
    async def get_stats(self, user_id: str) -> DecisionStats:
        """
        Get decision statistics for a user
        
        Args:
            user_id: User ID
            
        Returns:
            DecisionStats: Decision statistics
        """
        # Count by status
        total = await self.count_by_user(user_id)
        completed = await self.count_by_user(user_id, DecisionStatus.COMPLETED)
        pending = await self.count_by_user(user_id, DecisionStatus.PENDING)
        processing = await self.count_by_user(user_id, DecisionStatus.PROCESSING)
        failed = await self.count_by_user(user_id, DecisionStatus.FAILED)
        
        # Calculate averages from completed decisions
        pipeline = [
            {"$match": {"user_id": user_id, "status": DecisionStatus.COMPLETED}},
            {
                "$group": {
                    "_id": None,
                    "avg_processing_time": {"$avg": "$processing_time_ms"},
                    "avg_confidence": {"$avg": "$confidence.overall_score"},
                    "total_tokens": {"$sum": "$total_tokens"}
                }
            }
        ]
        
        result = await self.collection.aggregate(pipeline).to_list(length=1)
        
        avg_processing_time = None
        avg_confidence = None
        total_tokens = None
        
        if result:
            avg_processing_time = result[0].get("avg_processing_time")
            avg_confidence = result[0].get("avg_confidence")
            total_tokens = result[0].get("total_tokens")
        
        return DecisionStats(
            total_decisions=total,
            completed_decisions=completed,
            pending_decisions=pending + processing,
            failed_decisions=failed,
            avg_processing_time_ms=avg_processing_time,
            avg_confidence_score=avg_confidence,
            total_tokens_used=total_tokens
        )
    
    async def get_recent(
        self,
        user_id: str,
        days: int = 7,
        limit: int = 10
    ) -> List[DecisionInDB]:
        """
        Get recent decisions for a user
        
        Args:
            user_id: User ID
            days: Number of days to look back
            limit: Maximum number of decisions
            
        Returns:
            List[DecisionInDB]: Recent decisions
        """
        start_date = datetime.utcnow() - timedelta(days=days)
        
        return await self.get_by_user(
            user_id=user_id,
            start_date=start_date,
            limit=limit
        )


# Global repository instance
decision_repository = DecisionRepository()