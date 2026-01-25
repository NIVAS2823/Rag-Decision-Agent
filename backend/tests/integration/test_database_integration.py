"""
Database Integration Tests
==========================
End-to-end tests for database operations.
"""

import pytest_asyncio
import pytest
from datetime import datetime

from app.models.user import UserCreate, UserRole
from app.models.decision import DecisionCreate, DecisionStatus
from app.services.database import mongodb_manager, db_client
from app.services.database.repositories import user_repository, decision_repository


@pytest_asyncio.fixture
async def clean_database():
    """Setup and cleanup database"""
    await mongodb_manager.connect()
    await db_client.initialize()
    
    yield
    
    # Cleanup test data
    await user_repository.collection.delete_many({"email": {"$regex": "^integration.*@example.com$"}})
    await decision_repository.collection.delete_many({})
    await mongodb_manager.disconnect()


@pytest.mark.asyncio
async def test_complete_user_workflow(clean_database):
    """Test complete user lifecycle"""
    # Create user
    user_data = UserCreate(
        email="integration_user@example.com",
        password="SecurePass123",
        full_name="Integration Test User",
        role=UserRole.USER
    )
    user = await user_repository.create(user_data)
    
    assert user is not None
    assert user.email == "integration_user@example.com"
    
    # Get by ID
    found_user = await user_repository.get_by_id(str(user.id))
    assert found_user is not None
    assert found_user.email == user.email
    
    # Get by email
    found_by_email = await user_repository.get_by_email("integration_user@example.com")
    assert found_by_email is not None
    
    # Update user
    from app.models.user import UserUpdate
    update_data = UserUpdate(full_name="Updated Name")
    updated_user = await user_repository.update(str(user.id), update_data)
    assert updated_user.full_name == "Updated Name"
    
    # Soft delete
    result = await user_repository.soft_delete(str(user.id))
    assert result is True
    
    # Verify inactive
    inactive_user = await user_repository.get_by_id(str(user.id))
    assert inactive_user.is_active is False


@pytest.mark.asyncio
async def test_complete_decision_workflow(clean_database):
    """Test complete decision lifecycle"""
    # Create user first
    user_data = UserCreate(
        email="integration_decision_user@example.com",
        password="SecurePass123",
        full_name="Decision Test User"
    )
    user = await user_repository.create(user_data)
    
    # Create decision
    decision_data = DecisionCreate(
        query="Should we expand to international markets?",
        context="We have 100K users and $5M revenue",
        enable_web_search=True,
        enable_verification=True
    )
    decision = await decision_repository.create(str(user.id), decision_data)
    
    assert decision is not None
    assert decision.status == DecisionStatus.PENDING
    assert decision.user_id == str(user.id)
    
    # Update to processing
    processing = await decision_repository.update_status(
        str(decision.id),
        DecisionStatus.PROCESSING
    )
    assert processing.status == DecisionStatus.PROCESSING
    
    # Complete with results
    decision_output = {
        "recommendation": "Yes, proceed with expansion",
        "reasoning": "Strong market indicators",
        "pros": ["Growing market", "First-mover advantage"],
        "cons": ["High initial cost", "Regulatory complexity"],
        "risks": ["Currency fluctuation", "Political instability"],
        "alternatives": ["Focus on domestic growth first"],
        "next_steps": ["Market research", "Regulatory analysis"]
    }
    
    citations = [
        {
            "source_type": "web",
            "title": "International Market Report 2024",
            "excerpt": "Market growth projected at 25% annually",
            "url": "https://example.com/report",
            "relevance_score": 0.92
        }
    ]
    
    confidence = {
        "overall_score": 0.85,
        "level": "high",
        "factors": {
            "data_quality": 0.9,
            "source_reliability": 0.85,
            "claim_verification": 0.8
        },
        "reasoning": "High confidence based on multiple verified sources"
    }
    
    completed = await decision_repository.update_with_result(
        str(decision.id),
        decision_output=decision_output,
        citations=citations,
        confidence=confidence,
        processing_time_ms=3542.5,
        llm_model="gpt-4",
        total_tokens=2500,
        agent_trace_id="trace-123"
    )
    
    assert completed is not None
    assert completed.status == DecisionStatus.COMPLETED
    assert completed.decision is not None
    assert completed.processing_time_ms == 3542.5
    assert completed.completed_at is not None


@pytest.mark.asyncio
async def test_user_decision_relationship(clean_database):
    """Test relationship between users and decisions"""
    # Create user
    user_data = UserCreate(
        email="integration_relationship@example.com",
        password="SecurePass123",
        full_name="Relationship Test"
    )
    user = await user_repository.create(user_data)
    
    # Create multiple decisions for user
    decision_queries = [
        "Should we hire more engineers?",
        "Should we raise prices?",
        "Should we expand product features?"
    ]
    
    created_decisions = []
    for query in decision_queries:
        decision_data = DecisionCreate(query=query)
        decision = await decision_repository.create(str(user.id), decision_data)
        created_decisions.append(decision)
    
    # Get all decisions for user
    user_decisions = await decision_repository.get_by_user(str(user.id), limit=10)
    
    assert len(user_decisions) == 3
    assert all(d.user_id == str(user.id) for d in user_decisions)
    
    # Verify decisions are sorted by created_at (most recent first)
    for i in range(len(user_decisions) - 1):
        assert user_decisions[i].created_at >= user_decisions[i + 1].created_at


@pytest.mark.asyncio
async def test_decision_statistics(clean_database):
    """Test decision statistics calculation"""
    # Create user
    user_data = UserCreate(
        email="integration_stats@example.com",
        password="SecurePass123",
        full_name="Stats Test"
    )
    user = await user_repository.create(user_data)
    
    # Create decisions with different statuses
    for i in range(5):
        decision_data = DecisionCreate(query=f"Should we execute pagination test query {i}?")
        decision = await decision_repository.create(str(user.id), decision_data)
        
        # Complete 3 out of 5
        if i < 3:
            await decision_repository.update_with_result(
                str(decision.id),
                decision_output={
                    "recommendation": f"Recommendation {i}",
                    "reasoning": "Test",
                    "pros": [], "cons": [], "risks": [],
                    "alternatives": [], "next_steps": []
                },
                citations=[],
                confidence={
                    "overall_score": 0.8 + (i * 0.05),
                    "level": "high",
                    "factors": {},
                    "reasoning": "Test"
                },
                processing_time_ms=1000.0 + (i * 100),
                total_tokens=500 + (i * 50)
            )
        # Fail 1
        elif i == 3:
            await decision_repository.update_status(
                str(decision.id),
                DecisionStatus.FAILED,
                error_message="Test error"
            )
        # Leave 1 pending (i == 4)
    
    # Get statistics
    stats = await decision_repository.get_stats(str(user.id))
    
    assert stats.total_decisions == 5
    assert stats.completed_decisions == 3
    assert stats.pending_decisions == 1
    assert stats.failed_decisions == 1
    assert stats.avg_processing_time_ms is not None
    assert stats.avg_confidence_score is not None
    assert stats.total_tokens_used == 500 + 550 + 600  # Sum of completed


@pytest.mark.asyncio
async def test_pagination(clean_database):
    """Test pagination for decisions"""
    # Create user
    user_data = UserCreate(
        email="integration_pagination@example.com",
        password="SecurePass123",
        full_name="Pagination Test"
    )
    user = await user_repository.create(user_data)
    
    # Create 15 decisions
    for i in range(15):
        decision_data = DecisionCreate(
            query=f"Should we execute pagination test query number {i}?"
        )
        await decision_repository.create(str(user.id), decision_data)
    
    # Get first page (10 items)
    page1 = await decision_repository.get_by_user(str(user.id), skip=0, limit=10)
    assert len(page1) == 10
    
    # Get second page (5 items)
    page2 = await decision_repository.get_by_user(str(user.id), skip=10, limit=10)
    assert len(page2) == 5
    
    # Verify no overlap
    page1_ids = {str(d.id) for d in page1}
    page2_ids = {str(d.id) for d in page2}
    assert len(page1_ids.intersection(page2_ids)) == 0



@pytest.mark.asyncio
async def test_error_handling(clean_database):
    """Test error handling in database operations"""
    # Try to get non-existent user
    user = await user_repository.get_by_id("invalid_id")
    assert user is None
    
    # Try to get non-existent decision
    decision = await decision_repository.get_by_id("invalid_id")
    assert decision is None
    
    # Try to create user with duplicate email
    user_data = UserCreate(
        email="integration_duplicate@example.com",
        password="SecurePass123",
        full_name="Test"
    )
    await user_repository.create(user_data)
    
    with pytest.raises(ValueError, match="already exists"):
        await user_repository.create(user_data)


@pytest.mark.asyncio
async def test_concurrent_operations(clean_database):
    """Test concurrent database operations"""
    import asyncio
    
    # Create user
    user_data = UserCreate(
        email="integration_concurrent@example.com",
        password="SecurePass123",
        full_name="Concurrent Test"
    )
    user = await user_repository.create(user_data)
    
    # Create multiple decisions concurrently
    async def create_decision(index):
        decision_data = DecisionCreate(query=f"Concurrent query {index}?")
        return await decision_repository.create(str(user.id), decision_data)
    
    tasks = [create_decision(i) for i in range(10)]
    results = await asyncio.gather(*tasks)
    
    assert len(results) == 10
    assert all(r is not None for r in results)
    
    # Verify all were created
    decisions = await decision_repository.get_by_user(str(user.id), limit=20)
    assert len(decisions) == 10


@pytest.mark.asyncio
async def test_data_integrity(clean_database):
    """Test data integrity constraints"""
    # Create user and decision
    user_data = UserCreate(
        email="integration_integrity@example.com",
        password="SecurePass123",
        full_name="Integrity Test"
    )
    user = await user_repository.create(user_data)
    
    decision_data = DecisionCreate(query="Test query?")
    decision = await decision_repository.create(str(user.id), decision_data)
    
    # Verify timestamps
    assert decision.created_at is not None
    assert decision.updated_at is not None
    assert decision.created_at <= decision.updated_at
    
    # Update decision
    import asyncio
    await asyncio.sleep(0.1)  # Ensure time difference
    
    updated = await decision_repository.update_status(
        str(decision.id),
        DecisionStatus.PROCESSING
    )
    
    # Verify updated_at changed
    assert updated.updated_at > decision.updated_at


def test_database_integration_endpoint():
    from fastapi.testclient import TestClient
    from app.main import app

    with TestClient(app) as client:
        response = client.get("/api/v1/health/detailed")
        assert response.status_code == 200
    
    data = response.json()
    
    # Find MongoDB dependency
    mongodb_dep = next(
        (d for d in data["dependencies"] if d["name"] == "mongodb"),
        None
    )
    
    assert mongodb_dep is not None
    assert mongodb_dep["status"] in ["healthy", "unhealthy"]