"""
Utility functions for GrievTrack
Handles canonical payload generation, hashing, timestamps, and ID generation
"""

import hashlib
import json
from datetime import datetime, timezone
import uuid


def now_iso():
    """Get current timestamp in ISO format (UTC)"""
    return datetime.now(timezone.utc).isoformat()


def new_complaint_id():
    """Generate unique complaint ID"""
    return f"CMP-{uuid.uuid4().hex[:12].upper()}"


def new_event_id():
    """Generate unique event ID"""
    return f"EVT-{uuid.uuid4().hex[:12].upper()}"


def canonical_event_payload(complaint_id, event_id, event_type, actor_id, remarks, timestamp):
    """
    Create canonical event payload
    All fields are required; None/NULL becomes empty string
    """
    return {
        "complaint_id": complaint_id or "",
        "event_id": event_id or "",
        "event_type": event_type or "",
        "actor_id": actor_id or "",
        "remarks": remarks or "",
        "timestamp": timestamp or ""
    }


def canonical_json(payload):
    """
    Convert payload to canonical JSON string
    Deterministic: sorted keys, no whitespace
    """
    return json.dumps(payload, sort_keys=True, separators=(',', ':'))


def sha256(text):
    """Compute SHA-256 hash of text"""
    return hashlib.sha256(text.encode('utf-8')).hexdigest()
