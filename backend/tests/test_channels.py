import pytest


@pytest.mark.asyncio
async def test_create_channel(client, auth_headers):
    """Test creating a new channel."""
    response = await client.post("/api/channels/", json={
        "name": "test-channel",
        "description": "A test channel",
    }, headers=auth_headers)
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "test-channel"
    assert data["description"] == "A test channel"
    assert data["member_count"] == 1  # Creator auto-joined


@pytest.mark.asyncio
async def test_create_duplicate_channel(client, auth_headers):
    """Test creating a channel with duplicate name."""
    await client.post("/api/channels/", json={
        "name": "dup-channel",
    }, headers=auth_headers)
    response = await client.post("/api/channels/", json={
        "name": "dup-channel",
    }, headers=auth_headers)
    assert response.status_code == 409


@pytest.mark.asyncio
async def test_list_channels(client, auth_headers):
    """Test listing joined channels."""
    # Create a channel
    await client.post("/api/channels/", json={
        "name": "list-test",
    }, headers=auth_headers)

    response = await client.get("/api/channels/", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert len(data) >= 1
    names = [ch["name"] for ch in data]
    assert "list-test" in names


@pytest.mark.asyncio
async def test_join_channel(client, auth_headers, second_auth_headers):
    """Test joining a channel."""
    # Create channel as user 1
    create_resp = await client.post("/api/channels/", json={
        "name": "join-test",
    }, headers=auth_headers)
    channel_id = create_resp.json()["id"]

    # Join as user 2
    response = await client.post(
        f"/api/channels/{channel_id}/join",
        headers=second_auth_headers,
    )
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_leave_channel(client, auth_headers):
    """Test leaving a channel."""
    create_resp = await client.post("/api/channels/", json={
        "name": "leave-test",
    }, headers=auth_headers)
    channel_id = create_resp.json()["id"]

    response = await client.post(
        f"/api/channels/{channel_id}/leave",
        headers=auth_headers,
    )
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_get_channel(client, auth_headers):
    """Test getting channel details."""
    create_resp = await client.post("/api/channels/", json={
        "name": "detail-test",
        "description": "Detail test channel",
    }, headers=auth_headers)
    channel_id = create_resp.json()["id"]

    response = await client.get(
        f"/api/channels/{channel_id}",
        headers=auth_headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "detail-test"
