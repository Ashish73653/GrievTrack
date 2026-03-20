"""
Tests for GrievTrack utility functions
Tests canonical payload generation, hashing, and ID generation
"""

import re
from utils import canonical_event_payload, canonical_json, sha256, new_complaint_id, new_event_id


def test_canonical_event_payload():
    """Test canonical event payload creation"""
    # Use hardcoded timestamp in the exact format from now_iso()
    timestamp = "2026-03-20T10:00:00.000000+00:00"

    payload = canonical_event_payload(
        complaint_id="CMP-TEST123456",
        event_id="EVT-TEST123456",
        event_type="SUBMIT",
        actor_id="CIT001",
        remarks="Test complaint",
        timestamp=timestamp
    )

    assert payload["complaint_id"] == "CMP-TEST123456"
    assert payload["event_id"] == "EVT-TEST123456"
    assert payload["event_type"] == "SUBMIT"
    assert payload["actor_id"] == "CIT001"
    assert payload["remarks"] == "Test complaint"
    assert payload["timestamp"] == timestamp


def test_canonical_event_payload_with_none():
    """Test that None values become empty strings"""
    payload = canonical_event_payload(
        complaint_id=None,
        event_id=None,
        event_type=None,
        actor_id=None,
        remarks=None,
        timestamp=None
    )

    assert payload["complaint_id"] == ""
    assert payload["event_id"] == ""
    assert payload["event_type"] == ""
    assert payload["actor_id"] == ""
    assert payload["remarks"] == ""
    assert payload["timestamp"] == ""


def test_canonical_json():
    """Test canonical JSON serialization"""
    timestamp = "2026-03-20T10:00:00.000000+00:00"

    payload = {
        "complaint_id": "CMP-TEST",
        "event_id": "EVT-TEST",
        "event_type": "SUBMIT",
        "actor_id": "CIT001",
        "remarks": "Test",
        "timestamp": timestamp
    }

    json_str = canonical_json(payload)

    # Check that keys are sorted
    assert json_str.startswith('{"actor_id":')

    # Check no whitespace
    assert " " not in json_str
    assert "\n" not in json_str

    # Check specific format
    expected = '{"actor_id":"CIT001","complaint_id":"CMP-TEST","event_id":"EVT-TEST","event_type":"SUBMIT","remarks":"Test","timestamp":"2026-03-20T10:00:00.000000+00:00"}'
    assert json_str == expected


def test_canonical_json_deterministic():
    """Test that canonical JSON is deterministic"""
    timestamp = "2026-03-20T10:00:00.000000+00:00"

    # Create two identical payloads with different key orders
    payload1 = {
        "complaint_id": "CMP-TEST",
        "event_id": "EVT-TEST",
        "event_type": "SUBMIT",
        "actor_id": "CIT001",
        "remarks": "Test",
        "timestamp": timestamp
    }

    payload2 = {
        "timestamp": timestamp,
        "remarks": "Test",
        "actor_id": "CIT001",
        "event_type": "SUBMIT",
        "event_id": "EVT-TEST",
        "complaint_id": "CMP-TEST"
    }

    json1 = canonical_json(payload1)
    json2 = canonical_json(payload2)

    assert json1 == json2


def test_sha256():
    """Test SHA-256 hashing"""
    text = "test data"
    hash_value = sha256(text)

    # Check hash format (64 hex characters)
    assert len(hash_value) == 64
    assert all(c in "0123456789abcdef" for c in hash_value)

    # Check deterministic
    assert sha256(text) == sha256(text)

    # Check known hash
    expected = "916f0027a575074ce72a331777c3478d6513f786a591bd892da1a577bf2335f9"
    assert hash_value == expected


def test_sha256_of_canonical_json():
    """Test hashing of canonical JSON payload"""
    timestamp = "2026-03-20T10:00:00.000000+00:00"

    payload = canonical_event_payload(
        complaint_id="CMP-A1B2C3D4E5F6",
        event_id="EVT-X1Y2Z3A4B5C6",
        event_type="SUBMIT",
        actor_id="CIT001",
        remarks="Street light not working",
        timestamp=timestamp
    )

    json_str = canonical_json(payload)
    hash_value = sha256(json_str)

    # Verify hash is deterministic
    assert hash_value == sha256(canonical_json(payload))

    # Check hash format
    assert len(hash_value) == 64


def test_new_complaint_id():
    """Test complaint ID generation"""
    cid = new_complaint_id()

    # Check format: CMP-{12 hex chars uppercase}
    assert cid.startswith("CMP-")
    assert len(cid) == 16  # CMP- (4) + 12 chars

    hex_part = cid[4:]
    assert len(hex_part) == 12
    assert all(c in "0123456789ABCDEF" for c in hex_part)

    # Check uniqueness
    cid2 = new_complaint_id()
    assert cid != cid2


def test_new_event_id():
    """Test event ID generation"""
    eid = new_event_id()

    # Check format: EVT-{12 hex chars uppercase}
    assert eid.startswith("EVT-")
    assert len(eid) == 16  # EVT- (4) + 12 chars

    hex_part = eid[4:]
    assert len(hex_part) == 12
    assert all(c in "0123456789ABCDEF" for c in hex_part)

    # Check uniqueness
    eid2 = new_event_id()
    assert eid != eid2


def test_end_to_end_hash_anchoring():
    """Test complete workflow: payload → canonical JSON → hash"""
    timestamp = "2026-03-20T10:00:00.000000+00:00"

    # Step 1: Create payload
    payload = canonical_event_payload(
        complaint_id="CMP-123456789ABC",
        event_id="EVT-ABCDEF123456",
        event_type="SUBMIT",
        actor_id="CIT001",
        remarks="Test complaint for hash anchoring",
        timestamp=timestamp
    )

    # Step 2: Convert to canonical JSON
    json_str = canonical_json(payload)

    # Step 3: Compute hash
    hash_value = sha256(json_str)

    # Step 4: Verify deterministic
    hash_value2 = sha256(canonical_json(payload))
    assert hash_value == hash_value2

    # Step 5: Verify tampering detection
    payload["remarks"] = "Modified remarks"
    tampered_hash = sha256(canonical_json(payload))
    assert tampered_hash != hash_value
