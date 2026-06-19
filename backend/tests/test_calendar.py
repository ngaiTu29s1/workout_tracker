import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from backend.app.models.preset import WeeklyPreset

@pytest.mark.asyncio
async def test_calendar_preset_and_override(client: AsyncClient, db_session: AsyncSession):
    # Setup standard weekly presets
    presets = [
        WeeklyPreset(day_of_week=1, routine_tag="rest"), # Sunday
        WeeklyPreset(day_of_week=2, routine_tag="push"), # Monday
        WeeklyPreset(day_of_week=3, routine_tag="pull"), # Tuesday
        WeeklyPreset(day_of_week=4, routine_tag="legs"), # Wednesday
        WeeklyPreset(day_of_week=5, routine_tag="push"), # Thursday
        WeeklyPreset(day_of_week=6, routine_tag="pull"), # Friday
        WeeklyPreset(day_of_week=7, routine_tag="legs")  # Saturday
    ]
    db_session.add_all(presets)
    await db_session.commit()

    # 1. Fetch calendar for a week
    # Sunday, June 14, 2026 to Saturday, June 20, 2026
    response = await client.get("/api/calendar?start=2026-06-14&end=2026-06-20")
    assert response.status_code == 200
    events = response.json()["data"]
    assert len(events) == 7

    # Check Sunday has "rest" and Wednesday (June 17) has "legs"
    assert events[0]["date"] == "2026-06-14"
    assert events[0]["routine_tag"] == "rest"
    assert events[0]["is_override"] is False

    assert events[3]["date"] == "2026-06-17"
    assert events[3]["routine_tag"] == "legs"
    assert events[3]["is_override"] is False

    # 2. Add an override for Wednesday (June 17) to "push"
    override_payload = {
        "workout_date": "2026-06-17",
        "routine_tag": "push"
    }
    override_response = await client.post("/api/calendar/override", json=override_payload)
    assert override_response.status_code == 200
    assert override_response.json()["data"]["routine_tag"] == "push"

    # 3. Query calendar again to verify
    response_updated = await client.get("/api/calendar?start=2026-06-14&end=2026-06-20")
    events_updated = response_updated.json()["data"]

    # Wednesday (June 17) should be overridden
    assert events_updated[3]["date"] == "2026-06-17"
    assert events_updated[3]["routine_tag"] == "push"
    assert events_updated[3]["preset_tag"] == "legs"
    assert events_updated[3]["is_override"] is True

    # Other days (e.g. Monday) should remain presets
    assert events_updated[1]["date"] == "2026-06-15"
    assert events_updated[1]["routine_tag"] == "push"
    assert events_updated[1]["is_override"] is False

    # Revert override (routine_tag=None)
    revert_payload = {
        "workout_date": "2026-06-17",
        "routine_tag": None
    }
    revert_response = await client.post("/api/calendar/override", json=revert_payload)
    assert revert_response.status_code == 200
    
    # Query calendar again to verify it went back to "legs"
    response_reverted = await client.get("/api/calendar?start=2026-06-14&end=2026-06-20")
    events_reverted = response_reverted.json()["data"]
    assert events_reverted[3]["routine_tag"] == "legs"
    assert events_reverted[3]["is_override"] is False
