import pytest
from unittest.mock import patch, MagicMock, AsyncMock


@pytest.mark.asyncio
async def test_ai_summarize(client, auth_headers):
    """Test AI summarization endpoint with mocked Gemini response."""
    # Create channel and post messages
    create_resp = await client.post("/api/channels/", json={
        "name": "ai-test",
    }, headers=auth_headers)
    channel_id = create_resp.json()["id"]

    # Post some logistics messages
    messages = [
        "SHIP-1042 is delayed by 3 hours due to traffic on NH-44",
        "Warehouse Mumbai inventory check complete. 200 units ready for dispatch",
        "Route east driver confirmed pickup for 2PM slot",
        "ETA for SHIP-1001 updated to 6PM IST",
        "Need to escalate SHIP-1002 delay to manager - customs hold",
    ]
    for msg in messages:
        await client.post(
            f"/api/channels/{channel_id}/messages",
            json={"content": msg},
            headers=auth_headers,
        )

    # Mock the Gemini API response
    mock_summary = """📋 **Channel Summary** (last 24 hours)

**🚨 Urgent/Escalations:**
- SHIP-1002 is on customs hold - needs manager escalation

**📦 Shipment Updates:**
- SHIP-1042: Delayed 3 hours (traffic on NH-44)
- SHIP-1001: ETA updated to 6PM IST

**📝 Action Items:**
- Escalate SHIP-1002 customs hold to manager
- Confirm route east pickup at 2PM

**💬 Key Discussions:**
- Mumbai warehouse inventory check completed: 200 units ready for dispatch
"""

    mock_response = MagicMock()
    mock_response.text = mock_summary

    mock_model = MagicMock()
    mock_model.generate_content = MagicMock(return_value=mock_response)

    mock_genai_module = MagicMock()
    mock_genai_module.GenerativeModel.return_value = mock_model

    with patch.dict("sys.modules", {"google.generativeai": mock_genai_module}):
        response = await client.post("/api/ai/summarize", json={
            "channel_id": channel_id,
            "hours": 24,
        }, headers=auth_headers)

    assert response.status_code == 200
    data = response.json()
    assert "summary" in data
    assert "SHIP-1042" in data["summary"] or "Channel Summary" in data["summary"]


@pytest.mark.asyncio
async def test_ai_summarize_empty_channel(client, auth_headers):
    """Test AI summarization with no messages."""
    create_resp = await client.post("/api/channels/", json={
        "name": "empty-ai",
    }, headers=auth_headers)
    channel_id = create_resp.json()["id"]

    response = await client.post("/api/ai/summarize", json={
        "channel_id": channel_id,
        "hours": 24,
    }, headers=auth_headers)

    assert response.status_code == 200
    data = response.json()
    assert "No messages" in data["summary"]


@pytest.mark.asyncio
async def test_ai_summarize_no_auth(client):
    """Test AI summarization without authentication."""
    response = await client.post("/api/ai/summarize", json={
        "channel_id": "00000000-0000-0000-0000-000000000000",
        "hours": 24,
    })
    assert response.status_code == 403
