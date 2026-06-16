import pytest


@pytest.mark.asyncio
async def test_post_message(client, auth_headers):
    """Test posting a message to a channel."""
    # Create channel
    create_resp = await client.post("/api/channels/", json={
        "name": "msg-test",
    }, headers=auth_headers)
    channel_id = create_resp.json()["id"]

    # Post message
    response = await client.post(
        f"/api/channels/{channel_id}/messages",
        json={"content": "Hello, team!"},
        headers=auth_headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["content"] == "Hello, team!"
    assert data["sender_username"] == "testuser"
    assert data["message_type"] == "text"


@pytest.mark.asyncio
async def test_get_messages(client, auth_headers):
    """Test getting paginated messages."""
    # Create channel
    create_resp = await client.post("/api/channels/", json={
        "name": "history-test",
    }, headers=auth_headers)
    channel_id = create_resp.json()["id"]

    # Post several messages
    for i in range(5):
        await client.post(
            f"/api/channels/{channel_id}/messages",
            json={"content": f"Message {i}"},
            headers=auth_headers,
        )

    # Get messages
    response = await client.get(
        f"/api/channels/{channel_id}/messages?limit=3",
        headers=auth_headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert len(data["messages"]) == 3
    assert data["has_more"] is True


@pytest.mark.asyncio
async def test_post_message_not_member(client, auth_headers, second_auth_headers):
    """Test posting to a channel user hasn't joined."""
    create_resp = await client.post("/api/channels/", json={
        "name": "private-msg",
    }, headers=auth_headers)
    channel_id = create_resp.json()["id"]

    # Try to post as user 2 (not a member)
    response = await client.post(
        f"/api/channels/{channel_id}/messages",
        json={"content": "Unauthorized!"},
        headers=second_auth_headers,
    )
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_message_ordering(client, auth_headers):
    """Test that messages are returned in chronological order."""
    create_resp = await client.post("/api/channels/", json={
        "name": "order-test",
    }, headers=auth_headers)
    channel_id = create_resp.json()["id"]

    for i in range(3):
        await client.post(
            f"/api/channels/{channel_id}/messages",
            json={"content": f"Order-{i}"},
            headers=auth_headers,
        )

    response = await client.get(
        f"/api/channels/{channel_id}/messages",
        headers=auth_headers,
    )
    messages = response.json()["messages"]
    assert messages[0]["content"] == "Order-0"
    assert messages[1]["content"] == "Order-1"
    assert messages[2]["content"] == "Order-2"
