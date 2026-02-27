from datetime import datetime, timedelta

from fastapi.testclient import TestClient

from api.main import create_app


def test_order_preview_and_create():
    app = create_app()
    client = TestClient(app)

    preview_resp = client.post(
        "/orders/preview",
        json={
            "pickup_address": "Pickup Street",
            "drop_address": "Drop Street",
            "weight_kg": 1.0,
            "vehicle_type": "BIKE",
            "time_type": "STANDARD",
            "is_batch_eligible": True,
            "addons": [],
        },
    )
    assert preview_resp.status_code == 200
    preview = preview_resp.json()
    assert preview["total_cost"] >= 35.0

    pickup_slot = (datetime.utcnow() + timedelta(hours=2)).isoformat()
    create_resp = client.post(
        "/orders",
        json={
            "user_id": None,
            "preview": {
                "pickup_address": "Pickup Street",
                "drop_address": "Drop Street",
                "weight_kg": 1.0,
                "vehicle_type": "BIKE",
                "time_type": "STANDARD",
                "is_batch_eligible": True,
                "addons": [],
            },
            "pickup_slot": pickup_slot,
        },
    )
    assert create_resp.status_code in (200, 201)
    body = create_resp.json()
    assert body["order_number"].startswith("DLV-")

