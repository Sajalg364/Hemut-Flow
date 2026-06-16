import pytest


@pytest.mark.asyncio
async def test_register_success(client):
    """Test successful user registration."""
    response = await client.post("/api/auth/register", json={
        "username": "newuser",
        "email": "new@example.com",
        "password": "password123",
        "display_name": "New User",
    })
    assert response.status_code == 201
    data = response.json()
    assert "access_token" in data
    assert data["user"]["username"] == "newuser"
    assert data["user"]["email"] == "new@example.com"
    assert data["user"]["display_name"] == "New User"


@pytest.mark.asyncio
async def test_register_duplicate_username(client):
    """Test registration with duplicate username."""
    await client.post("/api/auth/register", json={
        "username": "dupuser",
        "email": "dup1@example.com",
        "password": "password123",
    })
    response = await client.post("/api/auth/register", json={
        "username": "dupuser",
        "email": "dup2@example.com",
        "password": "password123",
    })
    assert response.status_code == 409
    assert "already taken" in response.json()["detail"]


@pytest.mark.asyncio
async def test_register_duplicate_email(client):
    """Test registration with duplicate email."""
    await client.post("/api/auth/register", json={
        "username": "user1",
        "email": "same@example.com",
        "password": "password123",
    })
    response = await client.post("/api/auth/register", json={
        "username": "user2",
        "email": "same@example.com",
        "password": "password123",
    })
    assert response.status_code == 409
    assert "already registered" in response.json()["detail"]


@pytest.mark.asyncio
async def test_register_validation_short_password(client):
    """Test registration with too short password."""
    response = await client.post("/api/auth/register", json={
        "username": "validuser",
        "email": "valid@example.com",
        "password": "123",
    })
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_login_success(client):
    """Test successful login."""
    # Register first
    await client.post("/api/auth/register", json={
        "username": "loginuser",
        "email": "login@example.com",
        "password": "password123",
    })
    # Login
    response = await client.post("/api/auth/login", json={
        "username": "loginuser",
        "password": "password123",
    })
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["user"]["username"] == "loginuser"


@pytest.mark.asyncio
async def test_login_wrong_password(client):
    """Test login with wrong password."""
    await client.post("/api/auth/register", json={
        "username": "wrongpass",
        "email": "wrong@example.com",
        "password": "password123",
    })
    response = await client.post("/api/auth/login", json={
        "username": "wrongpass",
        "password": "wrongpassword",
    })
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_login_nonexistent_user(client):
    """Test login with non-existent user."""
    response = await client.post("/api/auth/login", json={
        "username": "nouser",
        "password": "password123",
    })
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_get_me(client, auth_headers):
    """Test getting current user info."""
    response = await client.get("/api/auth/me", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["username"] == "testuser"


@pytest.mark.asyncio
async def test_get_me_no_auth(client):
    """Test getting current user without auth."""
    response = await client.get("/api/auth/me")
    assert response.status_code == 403
