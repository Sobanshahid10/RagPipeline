import pytest
from httpx import AsyncClient
from app.config import settings
from app.core.security import decode_access_token


@pytest.mark.asyncio
async def test_register_new_user(client: AsyncClient):
    """Test 1: Register a new user: expect 200 with email in response."""
    payload = {
        "email": "alice@acme.corp",
        "password": "SecurePassword2026!",
        "tenant_name": "Acme Corporation"
    }
    response = await client.post(f"{settings.API_V1_STR}/auth/register", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["email"] == "alice@acme.corp"
    assert "id" in data
    assert "tenant_id" in data
    assert "admin" in data["roles"]


@pytest.mark.asyncio
async def test_login_correct_credentials(client: AsyncClient):
    """Test 2: Login with correct credentials: expect JWT token in response."""
    # Register user first
    reg_payload = {
        "email": "bob@enterprise.io",
        "password": "CorrectPassword123",
        "tenant_name": "Enterprise IO"
    }
    reg_res = await client.post(f"{settings.API_V1_STR}/auth/register", json=reg_payload)
    assert reg_res.status_code == 200

    # Login with OAuth2 form data
    login_data = {
        "username": "bob@enterprise.io",
        "password": "CorrectPassword123"
    }
    response = await client.post(
        f"{settings.API_V1_STR}/auth/login",
        data=login_data,
        headers={"Content-Type": "application/x-www-form-urlencoded"}
    )
    assert response.status_code == 200
    token_data = response.json()
    assert "access_token" in token_data
    assert token_data["token_type"] == "bearer"

    # Verify token payload
    decoded = decode_access_token(token_data["access_token"])
    assert decoded["email"] == "bob@enterprise.io"
    assert "sub" in decoded
    assert "tenant_id" in decoded


@pytest.mark.asyncio
async def test_login_wrong_password(client: AsyncClient):
    """Test 3: Login with wrong password: expect 401."""
    # Register user
    reg_payload = {
        "email": "carol@shield.org",
        "password": "RealPassword456",
        "tenant_name": "Shield Security"
    }
    await client.post(f"{settings.API_V1_STR}/auth/register", json=reg_payload)

    # Login with incorrect password
    login_data = {
        "username": "carol@shield.org",
        "password": "WrongPassword999"
    }
    response = await client.post(
        f"{settings.API_V1_STR}/auth/login",
        data=login_data,
        headers={"Content-Type": "application/x-www-form-urlencoded"}
    )
    assert response.status_code == 401
    assert "detail" in response.json()


@pytest.mark.asyncio
async def test_get_me_with_valid_token(client: AsyncClient):
    """Test 4: Access GET /me with valid token: expect user profile."""
    # Register and login
    email = "dave@techlabs.ai"
    password = "MyPassword789!"
    await client.post(
        f"{settings.API_V1_STR}/auth/register",
        json={"email": email, "password": password, "tenant_name": "TechLabs"}
    )

    login_res = await client.post(
        f"{settings.API_V1_STR}/auth/login",
        data={"username": email, "password": password},
        headers={"Content-Type": "application/x-www-form-urlencoded"}
    )
    token = login_res.json()["access_token"]

    # Access /me
    response = await client.get(
        f"{settings.API_V1_STR}/auth/me",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 200
    profile = response.json()
    assert profile["email"] == email
    assert "tenant_id" in profile
    assert profile["is_active"] is True


@pytest.mark.asyncio
async def test_get_me_without_token(client: AsyncClient):
    """Test 5: Access GET /me without token: expect 401."""
    response = await client.get(f"{settings.API_V1_STR}/auth/me")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_get_me_with_malformed_token(client: AsyncClient):
    """Test 6: Access GET /me with malformed token: expect 401."""
    response = await client.get(
        f"{settings.API_V1_STR}/auth/me",
        headers={"Authorization": "Bearer not.a.valid.jwt.token"}
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_register_duplicate_email(client: AsyncClient):
    """Test 7: Registering with an existing email returns 400 Bad Request."""
    payload = {
        "email": "duplicate@company.com",
        "password": "Password123!",
        "tenant_name": "Company One"
    }
    res1 = await client.post(f"{settings.API_V1_STR}/auth/register", json=payload)
    assert res1.status_code == 200

    # Attempt second registration with same email
    res2 = await client.post(
        f"{settings.API_V1_STR}/auth/register",
        json={"email": "duplicate@company.com", "password": "AnotherPassword456!", "tenant_name": "Company Two"}
    )
    assert res2.status_code == 400
    assert "already exists" in res2.json()["detail"]


@pytest.mark.asyncio
async def test_multi_tenant_isolation(client: AsyncClient):
    """Test 8: Verify multiple tenants and users have isolated tenant IDs and tokens."""
    # Register Tenant A
    user_a = {
        "email": "user.a@tenant-a.com",
        "password": "PasswordA123",
        "tenant_name": "Tenant Alpha"
    }
    res_a = await client.post(f"{settings.API_V1_STR}/auth/register", json=user_a)
    assert res_a.status_code == 200
    profile_a = res_a.json()

    # Register Tenant B
    user_b = {
        "email": "user.b@tenant-b.com",
        "password": "PasswordB456",
        "tenant_name": "Tenant Beta"
    }
    res_b = await client.post(f"{settings.API_V1_STR}/auth/register", json=user_b)
    assert res_b.status_code == 200
    profile_b = res_b.json()

    # Confirm different tenant IDs
    assert profile_a["tenant_id"] != profile_b["tenant_id"]

    # Login as User A
    login_a = await client.post(
        f"{settings.API_V1_STR}/auth/login",
        data={"username": user_a["email"], "password": user_a["password"]}
    )
    token_a = login_a.json()["access_token"]
    claims_a = decode_access_token(token_a)
    assert claims_a["tenant_id"] == profile_a["tenant_id"]

    # Login as User B
    login_b = await client.post(
        f"{settings.API_V1_STR}/auth/login",
        data={"username": user_b["email"], "password": user_b["password"]}
    )
    token_b = login_b.json()["access_token"]
    claims_b = decode_access_token(token_b)
    assert claims_b["tenant_id"] == profile_b["tenant_id"]
