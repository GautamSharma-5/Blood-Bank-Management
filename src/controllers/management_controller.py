from flask import Blueprint, render_template, request, redirect, url_for, flash, session, jsonify
from flask_mysqldb import MySQL
import MySQLdb.cursors
from datetime import datetime, timedelta

management_bp = Blueprint('management', __name__, url_prefix='/management')

mysql = None

def init_db(db):
    global mysql
    mysql = db

def management_staff_required(f):
    def decorated_function(*args, **kwargs):
        if 'logged_in' not in session or session.get('role') != 'management_staff':
            flash('You need to be logged in as management staff to access this page', 'danger')
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    decorated_function.__name__ = f.__name__
    return decorated_function

@management_bp.route('/dashboard')
@management_staff_required
def dashboard():
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    hospital_id = session.get('hospital_id')
    
    cursor.execute('SELECT SUM(units) as total_units FROM blood_inventory WHERE hospital_id = %s', (hospital_id,))
    total_units = cursor.fetchone()['total_units'] or 0
    
    cursor.execute('SELECT COUNT(*) as recent_requests FROM blood_requests WHERE hospital_id = %s AND request_date >= DATE_SUB(CURDATE(), INTERVAL 30 DAY)', (hospital_id,))
    recent_requests = cursor.fetchone()['recent_requests']
    
    cursor.execute('SELECT blood_type, units FROM blood_inventory WHERE hospital_id = %s ORDER BY blood_type', (hospital_id,))
    inventory_data = cursor.fetchall()
    
    cursor.execute('''
        SELECT r.request_id, r.requester_name, r.blood_type, r.units, r.request_date, r.status 
        FROM blood_requests r 
        WHERE r.hospital_id = %s
        ORDER BY r.request_date DESC LIMIT 5
    ''', (hospital_id,))
    recent_request_list = cursor.fetchall()
    
    return render_template('management/dashboard.html',
                         total_units=total_units,
                         recent_requests=recent_requests,
                         inventory_data=inventory_data,
                         recent_request_list=recent_request_list)

@management_bp.route('/inventory')
@management_staff_required
def inventory():
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute('''
        SELECT bi.*, 
               (SELECT SUM(units) FROM blood_requests WHERE blood_type = bi.blood_type AND status = 'approved') as units_requested
        FROM blood_inventory bi
        ORDER BY bi.blood_type
    ''')
    inventory = cursor.fetchall()
    
    return render_template('management/inventory.html', inventory=inventory)

@management_bp.route('/inventory/update/<blood_type>', methods=['GET', 'POST'])
@management_staff_required
def update_inventory(blood_type):
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute('SELECT * FROM blood_inventory WHERE blood_type = %s', (blood_type,))
    inventory_item = cursor.fetchone()
    
    if not inventory_item:
        flash('Blood type not found in inventory', 'danger')
        return redirect(url_for('management.inventory'))
    
    if request.method == 'POST':
        units = request.form.get('units', type=int)
        notes = request.form.get('notes')
        
        if units is None:
            flash('Please enter a valid number of units', 'danger')
            return redirect(url_for('management.update_inventory', blood_type=blood_type))
        
        cursor.execute('UPDATE blood_inventory SET units = %s, last_updated = %s, notes = %s WHERE blood_type = %s', 
                      (units, datetime.now(), notes, blood_type))
        mysql.connection.commit()
        
        cursor.execute('''
            INSERT INTO inventory_logs 
            (blood_type, previous_units, new_units, change_type, notes, updated_by, updated_at) 
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        ''', (blood_type, inventory_item['units'], units, 'manual', notes, session.get('username'), datetime.now()))
        mysql.connection.commit()
        
        flash('Inventory updated successfully', 'success')
        return redirect(url_for('management.inventory'))
    
    return render_template('management/update_inventory.html', inventory_item=inventory_item)

@management_bp.route('/requests')
@management_staff_required
def list_requests():
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute('''
        SELECT r.*, 
               (SELECT units FROM blood_inventory WHERE blood_type = r.blood_type) as available_units
        FROM blood_requests r 
        ORDER BY r.request_date DESC
    ''')
    requests = cursor.fetchall()
    
    return render_template('management/requests.html', requests=requests)

@management_bp.route('/requests/<int:request_id>')
@management_staff_required
def view_request(request_id):
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute('SELECT * FROM blood_requests WHERE request_id = %s', (request_id,))
    request_data = cursor.fetchone()
    
    if not request_data:
        flash('Request not found', 'danger')
        return redirect(url_for('management.list_requests'))
    
    cursor.execute('SELECT units FROM blood_inventory WHERE blood_type = %s', (request_data['blood_type'],))
    inventory = cursor.fetchone()
    available_units = inventory['units'] if inventory else 0
    
    return render_template('management/view_request.html', request=request_data, available_units=available_units)

@management_bp.route('/requests/<int:request_id>/process', methods=['POST'])
@management_staff_required
def process_request(request_id):
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute('SELECT * FROM blood_requests WHERE request_id = %s', (request_id,))
    request_data = cursor.fetchone()
    
    if not request_data:
        flash('Request not found', 'danger')
        return redirect(url_for('management.list_requests'))
    
    action = request.form.get('action')
    notes = request.form.get('notes')
    
    if action == 'approve':
        cursor.execute('SELECT units FROM blood_inventory WHERE blood_type = %s', (request_data['blood_type'],))
        inventory = cursor.fetchone()
        
        if not inventory or inventory['units'] < request_data['units']:
            flash('Not enough units available to approve this request', 'danger')
            return redirect(url_for('management.view_request', request_id=request_id))
        
        cursor.execute('UPDATE blood_requests SET status = %s, processed_by = %s, processed_at = %s, notes = %s WHERE request_id = %s', 
                      ('approved', session.get('username'), datetime.now(), notes, request_id))
        
        cursor.execute('UPDATE blood_inventory SET units = units - %s WHERE blood_type = %s', 
                      (request_data['units'], request_data['blood_type']))
        
        cursor.execute('''
            INSERT INTO inventory_logs 
            (blood_type, previous_units, new_units, change_type, reference_id, notes, updated_by, updated_at) 
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        ''', (request_data['blood_type'], inventory['units'], inventory['units'] - request_data['units'], 
              'request', request_id, f"Approved request #{request_id}", session.get('username'), datetime.now()))
        
        flash('Request approved successfully', 'success')
    
    elif action == 'reject':
        cursor.execute('UPDATE blood_requests SET status = %s, processed_by = %s, processed_at = %s, notes = %s WHERE request_id = %s', 
                      ('rejected', session.get('username'), datetime.now(), notes, request_id))
        
        flash('Request rejected', 'info')
    
    mysql.connection.commit()
    return redirect(url_for('management.list_requests'))

@management_bp.route('/reports')
@management_staff_required
def reports():
    return render_template('management/reports.html')

@management_bp.route('/api/reports/inventory-trend', methods=['GET'])
def api_inventory_trend():
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute('''
        SELECT blood_type, 
               DATE_FORMAT(updated_at, '%Y-%m-01') as month,
               AVG(new_units) as avg_units
        FROM inventory_logs
        WHERE updated_at >= DATE_SUB(CURDATE(), INTERVAL 6 MONTH)
        GROUP BY blood_type, DATE_FORMAT(updated_at, '%Y-%m-01')
        ORDER BY blood_type, month
    ''')
    data = cursor.fetchall()
    
    result = {}
    for item in data:
        blood_type = item['blood_type']
        if blood_type not in result:
            result[blood_type] = []
        
        result[blood_type].append({
            'month': item['month'],
            'units': item['avg_units']
        })
    
    return jsonify(result)

@management_bp.route('/expiry-tracking')
@management_staff_required
def expiry_tracking():
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute('''
        SELECT d.donation_id, d.blood_type, d.units, d.donation_date, 
               DATE_ADD(d.donation_date, INTERVAL 42 DAY) as expiry_date,
               DATEDIFF(DATE_ADD(d.donation_date, INTERVAL 42 DAY), CURDATE()) as days_until_expiry,
               dn.donor_id, dn.first_name, dn.last_name
        FROM donations d
        JOIN donors dn ON d.donor_id = dn.donor_id
        WHERE d.status = 'collected'
        AND DATEDIFF(DATE_ADD(d.donation_date, INTERVAL 42 DAY), CURDATE()) BETWEEN 0 AND 7
        ORDER BY days_until_expiry
    ''')
    expiring_units = cursor.fetchall()
    
    return render_template('management/expiry_tracking.html', expiring_units=expiring_units)

@management_bp.route('/hospitals')
@management_staff_required
def list_hospitals():
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute('SELECT * FROM hospitals ORDER BY name')
    hospitals = cursor.fetchall()
    
    return render_template('management/hospitals.html', hospitals=hospitals)

@management_bp.route('/hospitals/add', methods=['GET', 'POST'])
@management_staff_required
def add_hospital():
    if request.method == 'POST':
        name = request.form['name']
        address = request.form['address']
        phone = request.form['phone']
        email = request.form['email']
        contact_person = request.form['contact_person']
        
        if not name or not address or not phone:
            flash('Please fill all required fields', 'danger')
            return redirect(url_for('management.add_hospital'))
        
        cursor = mysql.connection.cursor()
        cursor.execute('''
            INSERT INTO hospitals 
            (name, address, phone, email, contact_person, registration_date) 
            VALUES (%s, %s, %s, %s, %s, %s)
        ''', (name, address, phone, email, contact_person, datetime.now()))
        mysql.connection.commit()
        
        flash('Hospital added successfully', 'success')
        return redirect(url_for('management.list_hospitals'))
    
    return render_template('management/add_hospital.html')