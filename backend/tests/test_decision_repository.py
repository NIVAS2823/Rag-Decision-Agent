"""
Tests for decision repository
"""
import pytest_asyncio
import pytest

from app.models.decision import (
    DecisionCreate,
    DecisionStatus,
)
from app.models.user import UserCreate, UserRole
from app.services.database import mongodb_manager
from app.services.database.repositories import decision_repository, user_repository


@pytest_asyncio.fixture
async def setup_database():
    """Setup database and create test user"""
    await mongodb_manager.connect()
    
    # Create test user
    user_data = UserCreate(
        email="decisiontest@example.com",
        password="SecurePass123",
        full_name="Decision Test User",
        role=UserRole.USER
    )
    user = await user_repository.create(user_data)
    
    yield str(user.id)
    
    # Cleanup
    await decision_repository.collection.delete_many({"user_id": str(user.id)})
    await user_repository.delete(str(user.id))
    await mongodb_manager.disconnect()


@pytest.mark.asyncio
async def test_create_decision(setup_database):
    """Test creating a decision"""
    user_id = setup_database
    
    decision_data = DecisionCreate(
        query="Should we expand our product line?",
        context="We currently have $2M in revenue",
        enable_web_search=True
    )
    
    decision = await decision_repository.create(user_id, decision_data)
    
    assert decision is not None
    assert decision.user_id == user_id
    assert decision.query == decision_data.query
    assert decision.status == DecisionStatus.PENDING
    assert decision.decision is None


@pytest.mark.asyncio
async def test_get_decision_by_id(setup_database):
    """Test getting decision by ID"""
    user_id = setup_database
    
    decision_data = DecisionCreate(
        query="Should we invest in cloud infrastructure?",
        context="Current infra is reaching capacity"
    )
    created = await decision_repository.create(user_id, decision_data)
    
    decision = await decision_repository.get_by_id(str(created.id))
    
    assert decision is not None
    assert str(decision.id) == str(created.id)
    assert decision.query == decision_data.query


@pytest.mark.asyncio
async def test_get_decisions_by_user(setup_database):
    """Test getting all decisions for a user"""
    user_id = setup_database
    
    for i in range(5):
        decision_data = DecisionCreate(
            query=f"Should we launch new product version {i}?",
            context=f"Market evaluation for version {i}"
        )
        await decision_repository.create(user_id, decision_data)
    
    decisions = await decision_repository.get_by_user(user_id, limit=10)
    
    assert len(decisions) == 5


@pytest.mark.asyncio
async def test_update_decision_status(setup_database):
    """Test updating decision status"""
    user_id = setup_database
    
    decision_data = DecisionCreate(
        query="Should we enter international markets?",
        context="Market growth analysis available"
    )
    created = await decision_repository.create(user_id, decision_data)
    
    updated = await decision_repository.update_status(
        str(created.id),
        DecisionStatus.PROCESSING
    )
    
    assert updated is not None
    assert updated.status == DecisionStatus.PROCESSING


@pytest.mark.asyncio
async def test_update_with_result(setup_database):
    """Test updating decision with AI results"""
    user_id = setup_database
    
    decision_data = DecisionCreate(
        query="Should we invest in generative AI research?",
        context="Competitive landscape evaluation"
    )
    created = await decision_repository.create(user_id, decision_data)
    
    decision_output = {
        "recommendation": "Proceed with phased investment",
        "reasoning": "Strong market demand and ROI potential",
        "pros": ["Innovation boost", "Market leadership"],
        "cons": ["High initial cost"],
        "risks": ["Technology maturity"],
        "alternatives": ["Incremental AI adoption"],
        "next_steps": ["Pilot project", "Infrastructure planning"]
    }
    
    citations = [
        {
            "source_type": "document",
            "title": "Market Report",
            "excerpt": "Strong AI market growth",
            "relevance_score": 0.9
        }
    ]
    
    confidence = {
        "overall_score": 0.85,
        "level": "high",
        "factors": {"market_trend": 0.9},
        "reasoning": "Strong supporting indicators"
    }
    
    updated = await decision_repository.update_with_result(
        str(created.id),
        decision_output=decision_output,
        citations=citations,
        confidence=confidence,
        processing_time_ms=1500.5,
        llm_model="gpt-4",
        total_tokens=1200
    )
    
    assert updated is not None
    assert updated.status == DecisionStatus.COMPLETED
    assert updated.decision is not None
    assert updated.processing_time_ms == 1500.5
    assert updated.completed_at is not None


@pytest.mark.asyncio
async def test_count_by_status(setup_database):
    """Test counting decisions by status"""
    user_id = setup_database
    
    for i in range(3):
        decision_data = DecisionCreate(
            query=f"Should we optimize backend architecture {i}?",
            context="System performance review"
        )
        decision = await decision_repository.create(user_id, decision_data)
        
        if i < 2:
            await decision_repository.update_status(
                str(decision.id),
                DecisionStatus.COMPLETED
            )
    
    total = await decision_repository.count_by_user(user_id)
    completed = await decision_repository.count_by_user(user_id, DecisionStatus.COMPLETED)
    pending = await decision_repository.count_by_user(user_id, DecisionStatus.PENDING)
    
    assert total == 3
    assert completed == 2
    assert pending == 1


@pytest.mark.asyncio
async def test_get_stats(setup_database):
    """Test getting decision statistics"""
    user_id = setup_database
    
    for i in range(3):
        decision_data = DecisionCreate(
            query=f"Should we redesign microservice pipeline {i}?",
            context="DevOps optimization study"
        )
        decision = await decision_repository.create(user_id, decision_data)
        
        if i < 2:
            await decision_repository.update_with_result(
                str(decision.id),
                decision_output={
                    "recommendation": "Proceed",
                    "reasoning": "Clear technical advantage",
                    "pros": [], "cons": [], "risks": [],
                    "alternatives": [], "next_steps": []
                },
                citations=[],
                confidence={
                    "overall_score": 0.8,
                    "level": "high",
                    "factors": {},
                    "reasoning": "Strong technical rationale"
                },
                processing_time_ms=1000.0,
                total_tokens=500
            )
    
    stats = await decision_repository.get_stats(user_id)
    
    assert stats.total_decisions == 3
    assert stats.completed_decisions == 2
    assert stats.pending_decisions == 1
    assert stats.avg_processing_time_ms is not None
    assert stats.avg_confidence_score is not None


@pytest.mark.asyncio
async def test_delete_decision(setup_database):
    """Test deleting a decision"""
    user_id = setup_database
    
    decision_data = DecisionCreate(
        query="Should we refactor legacy monolith system?",
        context="Scalability and maintenance concerns"
    )
    created = await decision_repository.create(user_id, decision_data)
    
    result = await decision_repository.delete(str(created.id))
    assert result is True
    
    decision = await decision_repository.get_by_id(str(created.id))
    assert decision is None
