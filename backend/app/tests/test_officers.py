import pytest
from tests.factories import create_role, create_user
from app.models.officers import OfficerPosition

# Test 1 — Admin/Webmaster can create an officer
@pytest.mark.asyncio
async def test_create_officer(client, db_session):
    # Create webmaster role + user
    webmaster_role = await create_role(db_session, "webmaster")
    user = await create_user(db_session, membership_number="99999", role=webmaster_role)

    # Login to get token
    login = await client.post("/api/auth/login", json={
        "membership_number": "99999",
        "password": "password"
    })
    token = login.json()["access_token"]

    # Create another user to assign as officer
    officer_user = await create_user(db_session, membership_number="88888")

    # Create officer
    response = await client.post(
        "/api/admin/officers/",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "user_id": officer_user.id,
            "position": OfficerPosition.grand_knight.value
        }
    )

    assert response.status_code == 200
    data = response.json()
    assert data["position"] == "grand_knight"

# Test 2 — Public endpoint returns correct officer data
@pytest.mark.asyncio
async def test_get_current_officers(client, db_session):
    # Create user + officer
    user = await create_user(db_session, membership_number="77777")
    await create_officer(db_session, user)

    response = await client.get("/api/officers/current")

    assert response.status_code == 200
    data = response.json()

    assert len(data) == 1
    assert data[0]["name"] == "John Doe"
    assert data[0]["photo"] == "/photos/john.jpg"
    assert data[0]["position"] == "grand_knight"

# Test 3 — Non-admin cannot create officers
@pytest.mark.asyncio
async def test_non_admin_cannot_create_officer(client, db_session):
    # Create normal user
    user = await create_user(db_session, membership_number="55555")

    # Login
    login = await client.post("/api/auth/login", json={
        "membership_number": "55555",
        "password": "password"
    })
    token = login.json()["access_token"]

    # Attempt to create officer
    response = await client.post(
        "/api/admin/officers/",
        headers={"Authorization": f"Bearer {token}"},
        json={"user_id": user.id, "position": "grand_knight"}
    )

    assert response.status_code == 403
