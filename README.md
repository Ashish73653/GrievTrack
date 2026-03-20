# GrievTrack - Blockchain-Ready Grievance Redressal System

**A research-driven, thesis-grade prototype demonstrating hash anchoring, verification, traceability, tamper detection, and comprehensive metrics for grievance management.**

## Overview

GrievTrack is a hybrid cloud-blockchain grievance redressal system implementing a **Citizen → Officer → Auditor** workflow with cryptographic hash anchoring and integrity verification. The system demonstrates:

- **Hash Anchoring**: Every complaint event is hashed (SHA-256) and anchored in a simulated ledger
- **Verification**: Auditors can verify event integrity by recomputing hashes
- **Traceability**: Complete timeline of complaint lifecycle events
- **Tamper Detection**: Immediate detection of unauthorized data modifications
- **Metrics**: EIS (Event Integrity Score), CVL (Compliance Verification Latency), OAI (Officer Accountability Index)
- **Blockchain Roadmap**: Hyperledger Fabric integration stub for future migration

## Architecture

### Technology Stack
- **Backend**: Flask (Python 3.8+)
- **Database**: SQLite (3 tables: complaints, complaint_events, ledger_hashes)
- **Frontend**: HTML5 + Jinja2 templates + CSS
- **Charts**: Chart.js (CDN)
- **Hashing**: SHA-256 (hashlib)

### Database Schema

**Table 1: complaints**
- complaint_id (PK)
- title, description, category, priority
- citizen_id, current_status, created_at

**Table 2: complaint_events**
- event_id (PK)
- complaint_id (FK), event_type, actor_id
- remarks, timestamp

**Table 3: ledger_hashes** (simulated blockchain ledger)
- ledger_id (PK, auto-increment)
- event_id, complaint_id, event_hash, timestamp

### Canonical Event Payload

All events use deterministic JSON serialization:

```json
{
  "actor_id": "...",
  "complaint_id": "...",
  "event_id": "...",
  "event_type": "...",
  "remarks": "...",
  "timestamp": "..."
}
```

**Rules**:
- Keys sorted alphabetically
- No whitespace in JSON
- NULL/None → empty string
- Timestamp in ISO 8601 UTC format
- SHA-256 hash of canonical JSON stored in ledger

## Installation & Setup

### Prerequisites
- Python 3.8 or higher
- pip (Python package manager)

### Step 1: Clone Repository

```bash
git clone https://github.com/Ashish73653/GrievTrack.git
cd GrievTrack
```

### Step 2: Create Virtual Environment

```bash
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

### Step 3: Install Dependencies

```bash
pip install -r requirements.txt
```

### Step 4: Initialize Database

```bash
python db.py
```

This creates `grievtrack.db` with the required schema.

### Step 5: Run Application

```bash
python app.py
```

The application will start at `http://localhost:5000`

### For GitHub Codespaces

The application is fully compatible with GitHub Codespaces:

1. Open repository in Codespaces
2. Run: `pip install -r requirements.txt`
3. Run: `python app.py`
4. Open forwarded port 5000 in browser

### Testing

Run the test suite to verify utility functions:

```bash
pip install pytest
pytest -q
```

Tests cover canonical payload generation, JSON serialization, hashing, and ID generation.

## Features & Routes

### 1. Dashboard (`/dashboard`)
- **Card 1**: Complaint Summary (total, open, closed)
- **Card 2**: Integrity Summary (total events, tampered, global EIS)
- **Card 3**: Officer Accountability (officers, delayed complaints, avg response time)
- **Card 4**: Audit Performance (audits run, avg CVL, last CVL)
- **Charts**: EIS trend, CVL trend

### 2. Submit Complaint (`/submit`)
**Citizen Module**
- Form: title, description, category, priority, citizen_id
- Creates complaint with status "SUBMIT"
- Generates event with SHA-256 hash
- Anchors hash to ledger
- Shows: complaint_id, event_hash, link to timeline

### 3. Update Status (`/update`)
**Officer Module**
- Form: complaint_id, officer_id, status (ASSIGNED/IN_PROGRESS/CLOSED), remarks
- Updates complaint status
- Creates new event with hash
- Anchors to ledger
- Shows: success confirmation, link to timeline

### 4. Timeline (`/timeline/<complaint_id>`)
**Traceability View**
- Displays complaint details
- Shows chronological event history table
- Columns: event_id, event_type, actor, remarks, timestamp

### 5. Audit (`/audit`)
**Auditor Module**

**Verify Integrity**:
- Input: complaint_id
- Recomputes hash for each event
- Compares with ledger hash
- Shows verification table with MATCH/TAMPERED status
- Displays metrics: EIS, CVL, OAI

**Simulate Tamper**:
- Modifies latest event remarks without updating ledger
- Demonstrates tamper detection capability

**Charts**:
- EIS over audit runs
- CVL over audit runs
- Event verification histogram

### 6. Reset (`/reset`)
**Demo Utility**
- Clears all data (complaints, events, ledger)
- Resets audit run history
- Requires confirmation

## Metrics Definitions

### EIS (Event Integrity Score)
**Formula**: `(matched_events / total_events) × 100`

- **100%**: All events match ledger (no tampering)
- **< 100%**: Tampering detected
- Displayed in audit results and dashboard

### CVL (Compliance Verification Latency)
**Measurement**: Time to verify all events for a complaint (milliseconds)

- Measures audit performance
- Tracked per audit run
- Lower is better

### OAI (Officer Accountability Index)
**SLA-based metric**:
- Measures time from ASSIGNED → first action (IN_PROGRESS or CLOSED)
- Thresholds:
  - **Urgent**: 24 hours
  - **Normal**: 7 days (168 hours)
  - **Non-urgent**: 30 days (720 hours)
- Status: Within SLA / Delayed

## Demo Workflow (2-Minute Viva)

### Step 1: Submit Complaint (Citizen)
```
1. Navigate to /submit
2. Fill form:
   - Title: "Street light not working"
   - Description: "Main street light broken for 3 days"
   - Category: "Infrastructure"
   - Priority: "Urgent"
   - Citizen ID: "CIT001"
3. Submit
4. Note complaint_id (e.g., CMP-A1B2C3D4E5F6)
5. Note event hash anchored
```

### Step 2: Update Status (Officer)
```
1. Navigate to /update
2. Update 1:
   - Complaint ID: CMP-A1B2C3D4E5F6
   - Officer ID: OFF001
   - Status: ASSIGNED
   - Remarks: "Assigned to maintenance team"
3. Update 2:
   - Status: IN_PROGRESS
   - Remarks: "Team dispatched to location"
4. Update 3:
   - Status: CLOSED
   - Remarks: "Light repaired and tested"
```

### Step 3: View Timeline (Traceability)
```
1. Navigate to /timeline/CMP-A1B2C3D4E5F6
2. Observe chronological events:
   - SUBMIT → ASSIGNED → IN_PROGRESS → CLOSED
3. Each event shows actor, timestamp, remarks
```

### Step 4: Verify Integrity (Auditor)
```
1. Navigate to /audit
2. Enter complaint_id: CMP-A1B2C3D4E5F6
3. Click "Verify Integrity"
4. Observe:
   - All events show "MATCH"
   - EIS = 100%
   - CVL displayed (e.g., 12.5 ms)
   - OAI shows "Within SLA" (response < 24 hours for Urgent)
5. Charts display audit history
```

### Step 5: Simulate Tamper (Auditor)
```
1. In /audit, click "Simulate Tamper"
2. System modifies latest event without updating ledger
3. Click "Verify Integrity" again
4. Observe:
   - One event shows "TAMPERED"
   - EIS < 100% (e.g., 75%)
   - Charts update showing integrity drop
```

### Step 6: Dashboard Overview
```
1. Navigate to /dashboard
2. View summary cards:
   - Complaints: 1 total, 0 open, 1 closed
   - Integrity: 4 events, 1 tampered, 75% EIS
   - Accountability: 1 officer, 0 delayed, avg response shown
   - Audit Performance: runs, avg CVL
3. Charts show trends
```

### Step 7: Blockchain Roadmap
```
1. Mention: fabric_stub/ folder contains:
   - chaincode_pseudocode.txt (Fabric smart contract logic)
   - sample_payload.json (canonical payload example)
2. Explain: SQLite ledger can be replaced with Fabric client calls
3. No changes needed to hashing, payloads, or UI
```

## Research Mapping

### How GrievTrack Addresses Research Objectives

**Objective 1: Immutable Audit Trail**
- ✅ Every event hashed (SHA-256) and anchored
- ✅ Ledger simulation demonstrates concept
- ✅ Ready for Fabric migration

**Objective 2: Tamper Detection**
- ✅ Hash verification compares recomputed vs ledger
- ✅ Mismatch immediately flagged
- ✅ Demonstrated via simulate tamper feature

**Objective 3: Accountability**
- ✅ Every event records actor_id
- ✅ OAI metric measures officer response time
- ✅ SLA thresholds enforce accountability

**Objective 4: Transparency**
- ✅ Complete timeline visible to stakeholders
- ✅ Event history traceable
- ✅ Dashboard shows system-wide metrics

**Objective 5: Scalability Readiness**
- ✅ Hyperledger Fabric stub demonstrates blockchain path
- ✅ Modular architecture supports cloud/blockchain hybrid
- ✅ No vendor lock-in (open-source stack)

## Hyperledger Fabric Integration

### Current: SQLite Ledger Simulation
```python
# In app.py:
cursor.execute('''
    INSERT INTO ledger_hashes (event_id, complaint_id, event_hash, timestamp)
    VALUES (?, ?, ?, ?)
''', (event_id, complaint_id, event_hash, timestamp))
```

### Future: Fabric Chaincode
```python
# Replace with:
fabric_client.chaincode_invoke(
    channel_name='grievtrack-channel',
    cc_name='grievtrack',
    fcn='AnchorHash',
    args=[event_id, complaint_id, event_hash, timestamp]
)
```

**Benefits**:
- Immutable ledger (no SQL tamper)
- Distributed consensus
- Multi-organization trust
- Smart contract automation

**See**: `fabric_stub/` for integration details

## File Structure

```
GrievTrack/
├── app.py                  # Flask routes and controller logic
├── db.py                   # Database schema and initialization
├── utils.py                # Canonical payload, hashing, timestamps, IDs
├── requirements.txt        # Python dependencies
├── README.md               # This file
├── templates/
│   ├── base.html           # Base template with navigation
│   ├── submit.html         # Citizen module
│   ├── update.html         # Officer module
│   ├── timeline.html       # Traceability view
│   ├── audit.html          # Auditor module with charts
│   ├── dashboard.html      # Overview with metrics
│   └── reset.html          # Demo reset utility
├── static/
│   └── style.css           # Minimal CSS styling
└── fabric_stub/
    ├── chaincode_pseudocode.txt  # Fabric smart contract logic
    └── sample_payload.json       # Canonical payload example
```

## Constraints & Design Decisions

### Hard Constraints (Met)
1. ✅ Exactly 3 database tables (no more, no less)
2. ✅ Canonical, deterministic JSON + SHA-256
3. ✅ All required routes working
4. ✅ Fabric stub folder included
5. ✅ No external cloud credentials required
6. ✅ Codespaces-ready

### Design Decisions
- **In-memory audit runs**: Charts require historical data, but adding a 4th table violates constraints. Solution: Python global list (session-based)
- **SQLite over PostgreSQL**: Simpler setup, no external services needed
- **Chart.js CDN**: No npm/build step required
- **Minimal CSS**: Research-grade ≠ production-grade UI polish
- **Flask debug mode**: Enabled for demo; disable in production

## Troubleshooting

### Database not found
```bash
python db.py  # Re-initialize
```

### Port 5000 already in use
```bash
# Change port in app.py:
app.run(debug=True, host='0.0.0.0', port=5001)
```

### Charts not displaying
- Ensure internet connection (Chart.js from CDN)
- Check browser console for errors
- Verify audit runs exist (run at least one audit)

### Hash mismatch on fresh data
- Should not occur with canonical payload
- Check timestamp format consistency
- Verify no NULL handling issues

## Future Enhancements

1. **Hyperledger Fabric Integration**
   - Deploy chaincode from `fabric_stub/`
   - Replace SQLite ledger calls with Fabric client
   - Test on multi-org network

2. **Authentication & Authorization**
   - Role-based access control (Citizen/Officer/Auditor)
   - JWT tokens for API security

3. **Advanced Metrics**
   - Average resolution time by category
   - Officer performance rankings
   - Geographic complaint clustering

4. **Notifications**
   - Email/SMS on status updates
   - Real-time WebSocket updates

5. **Mobile App**
   - React Native or Flutter frontend
   - REST API backend (Flask)

## License

This project is created for educational and research purposes.

## Contact

**Repository**: https://github.com/Ashish73653/GrievTrack
**Issues**: https://github.com/Ashish73653/GrievTrack/issues

## Acknowledgments

- Developed as a thesis-grade prototype for grievance redressal research
- Demonstrates blockchain-ready architecture without requiring paid services
- Designed for GitHub Codespaces and local development
- Built with Flask, SQLite, and Chart.js

---

**Version**: 1.0.0
**Date**: 2026-03-20
**Status**: Research Prototype Ready
