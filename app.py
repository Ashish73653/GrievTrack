"""
GrievTrack - Grievance Redressal System with Hash Anchoring
Flask application implementing Citizen -> Officer -> Auditor workflow
"""

from flask import Flask, render_template, request, redirect, url_for, flash, session
import os
from db import init_db, get_db, close_db
from utils import (
    canonical_event_payload,
    canonical_json,
    sha256,
    now_iso,
    new_complaint_id,
    new_event_id
)

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-production')
app.teardown_appcontext(close_db)

# In-memory audit run tracking for charts (session-based)
audit_runs = []


@app.route('/')
def index():
    """Redirect to dashboard"""
    return redirect(url_for('dashboard'))


@app.route('/submit', methods=['GET', 'POST'])
def submit():
    """Citizen module: Submit complaint"""
    if request.method == 'POST':
        # Get form data
        title = request.form.get('title', '').strip()
        description = request.form.get('description', '').strip()
        category = request.form.get('category', '').strip()
        priority = request.form.get('priority', 'Normal')
        citizen_id = request.form.get('citizen_id', '').strip()

        # Validate
        if not all([title, description, category, citizen_id]):
            flash('All fields are required', 'error')
            return render_template('submit.html')

        # Generate complaint ID
        complaint_id = new_complaint_id()
        event_id = new_event_id()
        timestamp = now_iso()

        db = get_db()
        cursor = db.cursor()

        # Insert complaint
        cursor.execute('''
            INSERT INTO complaints (complaint_id, title, description, category, priority,
                                    citizen_id, current_status, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (complaint_id, title, description, category, priority, citizen_id, 'SUBMIT', timestamp))

        # Insert first event
        remarks = "Complaint submitted"
        cursor.execute('''
            INSERT INTO complaint_events (event_id, complaint_id, event_type, actor_id, remarks, timestamp)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (event_id, complaint_id, 'SUBMIT', citizen_id, remarks, timestamp))

        # Create canonical payload and compute hash
        payload = canonical_event_payload(complaint_id, event_id, 'SUBMIT', citizen_id, remarks, timestamp)
        canonical = canonical_json(payload)
        event_hash = sha256(canonical)

        # Store in ledger
        cursor.execute('''
            INSERT INTO ledger_hashes (event_id, complaint_id, event_hash, timestamp)
            VALUES (?, ?, ?, ?)
        ''', (event_id, complaint_id, event_hash, timestamp))

        db.commit()

        flash('Complaint submitted successfully!', 'success')
        return render_template('submit.html', success=True, complaint_id=complaint_id,
                             event_hash=event_hash)

    return render_template('submit.html')


@app.route('/update', methods=['GET', 'POST'])
def update():
    """Officer module: Update complaint status"""
    if request.method == 'POST':
        complaint_id = request.form.get('complaint_id', '').strip()
        officer_id = request.form.get('officer_id', '').strip()
        status = request.form.get('status', '').strip()
        remarks = request.form.get('remarks', '').strip()

        if not all([complaint_id, officer_id, status]):
            flash('Complaint ID, Officer ID, and Status are required', 'error')
            return render_template('update.html')

        db = get_db()
        cursor = db.cursor()

        # Validate complaint exists
        cursor.execute('SELECT complaint_id FROM complaints WHERE complaint_id = ?', (complaint_id,))
        if not cursor.fetchone():
            flash('Complaint not found', 'error')
            return render_template('update.html')

        # Update complaint status
        cursor.execute('UPDATE complaints SET current_status = ? WHERE complaint_id = ?',
                      (status, complaint_id))

        # Insert new event
        event_id = new_event_id()
        timestamp = now_iso()
        cursor.execute('''
            INSERT INTO complaint_events (event_id, complaint_id, event_type, actor_id, remarks, timestamp)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (event_id, complaint_id, status, officer_id, remarks, timestamp))

        # Create canonical payload and compute hash
        payload = canonical_event_payload(complaint_id, event_id, status, officer_id, remarks, timestamp)
        canonical = canonical_json(payload)
        event_hash = sha256(canonical)

        # Store in ledger
        cursor.execute('''
            INSERT INTO ledger_hashes (event_id, complaint_id, event_hash, timestamp)
            VALUES (?, ?, ?, ?)
        ''', (event_id, complaint_id, event_hash, timestamp))

        db.commit()

        flash('Complaint updated successfully!', 'success')
        return render_template('update.html', success=True, complaint_id=complaint_id)

    return render_template('update.html')


@app.route('/timeline/<complaint_id>')
def timeline(complaint_id):
    """Display complaint timeline"""
    db = get_db()
    cursor = db.cursor()

    # Get complaint
    cursor.execute('SELECT * FROM complaints WHERE complaint_id = ?', (complaint_id,))
    complaint = cursor.fetchone()

    if not complaint:
        flash('Complaint not found', 'error')
        return redirect(url_for('dashboard'))

    # Get events
    cursor.execute('''
        SELECT event_id, event_type, actor_id, remarks, timestamp
        FROM complaint_events
        WHERE complaint_id = ?
        ORDER BY timestamp ASC
    ''', (complaint_id,))
    events = cursor.fetchall()

    return render_template('timeline.html', complaint=complaint, events=events)


@app.route('/audit', methods=['GET', 'POST'])
def audit():
    """Auditor module: Verification, tamper simulation, metrics"""
    verification_results = None
    metrics = None

    if request.method == 'POST':
        complaint_id = request.form.get('complaint_id', '').strip()
        action = request.form.get('action', '')

        if not complaint_id:
            flash('Complaint ID is required', 'error')
            return render_template('audit.html', audit_runs=audit_runs)

        db = get_db()
        cursor = db.cursor()

        # Check complaint exists
        cursor.execute('SELECT complaint_id, priority FROM complaints WHERE complaint_id = ?', (complaint_id,))
        complaint_data = cursor.fetchone()
        if not complaint_data:
            flash('Complaint not found', 'error')
            return render_template('audit.html', audit_runs=audit_runs)

        priority = complaint_data[1] if complaint_data else 'Normal'

        if action == 'tamper':
            # Simulate tamper: modify latest event remarks without updating ledger
            cursor.execute('''
                SELECT event_id FROM complaint_events
                WHERE complaint_id = ?
                ORDER BY timestamp DESC LIMIT 1
            ''', (complaint_id,))
            latest_event = cursor.fetchone()
            if latest_event:
                cursor.execute('''
                    UPDATE complaint_events
                    SET remarks = remarks || ' [TAMPERED]'
                    WHERE event_id = ?
                ''', (latest_event[0],))
                db.commit()
                flash('Tamper simulated on latest event', 'warning')

        # Verify integrity
        import time
        start_time = time.time()

        cursor.execute('''
            SELECT event_id, complaint_id, event_type, actor_id, remarks, timestamp
            FROM complaint_events
            WHERE complaint_id = ?
            ORDER BY timestamp ASC
        ''', (complaint_id,))
        events = cursor.fetchall()

        verification_results = []
        matched_count = 0
        total_count = len(events)

        for event in events:
            event_id, cid, event_type, actor_id, remarks, timestamp = event

            # Recompute hash
            payload = canonical_event_payload(cid, event_id, event_type, actor_id, remarks, timestamp)
            canonical = canonical_json(payload)
            recomputed_hash = sha256(canonical)

            # Get ledger hash
            cursor.execute('SELECT event_hash FROM ledger_hashes WHERE event_id = ?', (event_id,))
            ledger_row = cursor.fetchone()
            ledger_hash = ledger_row[0] if ledger_row else None

            match = (recomputed_hash == ledger_hash)
            if match:
                matched_count += 1

            verification_results.append({
                'event_id': event_id,
                'event_type': event_type,
                'recomputed_hash': recomputed_hash[:16] + '...',
                'ledger_hash': ledger_hash[:16] + '...' if ledger_hash else 'N/A',
                'result': 'MATCH' if match else 'TAMPERED'
            })

        cvl_ms = (time.time() - start_time) * 1000
        eis = (matched_count / total_count * 100) if total_count > 0 else 0

        # Calculate OAI (Officer Accountability)
        oai_result = calculate_oai(cursor, complaint_id, priority)

        metrics = {
            'total': total_count,
            'matched': matched_count,
            'tampered': total_count - matched_count,
            'eis': round(eis, 2),
            'cvl_ms': round(cvl_ms, 2),
            'oai': oai_result
        }

        # Store audit run
        audit_runs.append({
            'timestamp': now_iso(),
            'complaint_id': complaint_id,
            'eis': metrics['eis'],
            'cvl_ms': metrics['cvl_ms'],
            'matched': matched_count,
            'total': total_count
        })

    return render_template('audit.html', verification_results=verification_results,
                          metrics=metrics, audit_runs=audit_runs)


def calculate_oai(cursor, complaint_id, priority):
    """Calculate Officer Accountability Index for a complaint"""
    # Get ASSIGNED timestamp
    cursor.execute('''
        SELECT timestamp FROM complaint_events
        WHERE complaint_id = ? AND event_type = 'ASSIGNED'
        ORDER BY timestamp ASC LIMIT 1
    ''', (complaint_id,))
    assigned_row = cursor.fetchone()

    if not assigned_row:
        return {'status': 'N/A', 'reason': 'Not yet assigned'}

    t_assign = assigned_row[0]

    # Get first action (IN_PROGRESS or CLOSED)
    cursor.execute('''
        SELECT timestamp FROM complaint_events
        WHERE complaint_id = ? AND event_type IN ('IN_PROGRESS', 'CLOSED')
        ORDER BY timestamp ASC LIMIT 1
    ''', (complaint_id,))
    action_row = cursor.fetchone()

    if not action_row:
        return {'status': 'Pending', 'reason': 'No action taken yet'}

    t_action = action_row[0]

    # Calculate response time
    from datetime import datetime
    dt_assign = datetime.fromisoformat(t_assign.replace('Z', '+00:00'))
    dt_action = datetime.fromisoformat(t_action.replace('Z', '+00:00'))
    response_seconds = (dt_action - dt_assign).total_seconds()
    response_hours = response_seconds / 3600

    # SLA thresholds
    sla_thresholds = {
        'Urgent': 24,
        'Normal': 7 * 24,
        'Non-urgent': 30 * 24
    }
    threshold = sla_thresholds.get(priority, 7 * 24)

    within_sla = response_hours <= threshold

    return {
        'response_hours': round(response_hours, 2),
        'sla_hours': threshold,
        'within_sla': within_sla,
        'status': 'Within SLA' if within_sla else 'Delayed'
    }


@app.route('/dashboard')
def dashboard():
    """Dashboard with summary cards and charts"""
    db = get_db()
    cursor = db.cursor()

    # Card 1: Complaint Summary
    cursor.execute('SELECT COUNT(*) FROM complaints')
    total_complaints = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM complaints WHERE current_status != 'CLOSED'")
    open_complaints = cursor.fetchone()[0]

    closed_complaints = total_complaints - open_complaints

    # Card 2: Integrity Summary (global scan)
    cursor.execute('SELECT event_id, complaint_id, event_type, actor_id, remarks, timestamp FROM complaint_events')
    all_events = cursor.fetchall()

    total_events = len(all_events)
    tampered_events = 0

    for event in all_events:
        event_id, cid, event_type, actor_id, remarks, timestamp = event
        payload = canonical_event_payload(cid, event_id, event_type, actor_id, remarks, timestamp)
        canonical = canonical_json(payload)
        recomputed_hash = sha256(canonical)

        cursor.execute('SELECT event_hash FROM ledger_hashes WHERE event_id = ?', (event_id,))
        ledger_row = cursor.fetchone()
        ledger_hash = ledger_row[0] if ledger_row else None

        if recomputed_hash != ledger_hash:
            tampered_events += 1

    global_eis = ((total_events - tampered_events) / total_events * 100) if total_events > 0 else 100

    # Card 3: Officer Accountability
    cursor.execute("SELECT DISTINCT actor_id FROM complaint_events WHERE event_type IN ('ASSIGNED', 'IN_PROGRESS', 'CLOSED')")
    officers = cursor.fetchall()
    total_officers = len(officers)

    # Count delayed complaints
    cursor.execute('SELECT complaint_id, priority FROM complaints')
    complaints = cursor.fetchall()
    delayed_count = 0
    total_response_time = 0
    response_count = 0

    for cid, priority in complaints:
        oai = calculate_oai(cursor, cid, priority)
        if oai.get('within_sla') is False:
            delayed_count += 1
        if 'response_hours' in oai:
            total_response_time += oai['response_hours']
            response_count += 1

    avg_response_hours = (total_response_time / response_count) if response_count > 0 else 0

    # Card 4: Audit Performance
    audit_count = len(audit_runs)
    avg_cvl = sum(run['cvl_ms'] for run in audit_runs) / audit_count if audit_count > 0 else 0
    last_cvl = audit_runs[-1]['cvl_ms'] if audit_runs else 0

    summary = {
        'complaints': {
            'total': total_complaints,
            'open': open_complaints,
            'closed': closed_complaints
        },
        'integrity': {
            'total_events': total_events,
            'tampered': tampered_events,
            'eis': round(global_eis, 2)
        },
        'accountability': {
            'total_officers': total_officers,
            'delayed': delayed_count,
            'avg_response_hours': round(avg_response_hours, 2)
        },
        'audit': {
            'total_audits': audit_count,
            'avg_cvl': round(avg_cvl, 2),
            'last_cvl': round(last_cvl, 2)
        }
    }

    return render_template('dashboard.html', summary=summary, audit_runs=audit_runs)


@app.route('/reset', methods=['GET', 'POST'])
def reset():
    """Reset database (for demo purposes)"""
    if request.method == 'POST':
        db = get_db()
        cursor = db.cursor()
        cursor.execute('DELETE FROM ledger_hashes')
        cursor.execute('DELETE FROM complaint_events')
        cursor.execute('DELETE FROM complaints')
        db.commit()

        # Clear audit runs
        audit_runs.clear()

        flash('Database reset successfully', 'success')
        return redirect(url_for('dashboard'))

    return render_template('reset.html')


@app.errorhandler(404)
def not_found(e):
    return render_template('base.html', error='Page not found'), 404


@app.errorhandler(500)
def server_error(e):
    return render_template('base.html', error='Internal server error'), 500


if __name__ == '__main__':
    # Initialize database
    init_db()
    app.run(debug=True, host='0.0.0.0', port=5000)
