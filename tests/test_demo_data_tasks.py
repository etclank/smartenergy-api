# tests/test_demo_data_tasks.py
import pytest
from app.models import User, Site, Meter
from app.tasks.demo_data import generate_demo_data, clean_demo_data


@pytest.mark.asyncio
async def test_generate_and_clean_demo_data(db_session):
    """Generate demo data and then clean it, verifying inserts and deletes."""

    # Create a user first (since Site.user_id is NOT NULL)
    user = User(username="demo_user", email="demo@example.com", hashed_password="x")
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)

    # Create a Site linked to that user
    site = Site(name="DemoSite", location="DemoLocation", user_id=user.id)
    db_session.add(site)
    await db_session.commit()
    await db_session.refresh(site)

    # Seed one meter under this site
    m = Meter(
        name="TestMeter",
        serial_number="ABC123",
        location="DemoLocation",
        type="electric",
        site_id=site.id,
    )
    db_session.add(m)
    await db_session.commit()

    # Generate and then clean demo data
    res = await generate_demo_data(days=1)
    assert res["inserted"] > 0

    res2 = await clean_demo_data(older_than_days=10000)
    assert "deleted" in res2
