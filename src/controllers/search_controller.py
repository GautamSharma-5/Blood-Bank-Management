from flask import Blueprint, render_template, request, jsonify
from flask_mysqldb import MySQL
import MySQLdb.cursors

search_bp = Blueprint('search', __name__, url_prefix='/search')

# MySQL instance will be initialized later
mysql = None

def init_db(db):
    global mysql
    mysql = db

@search_bp.route('/')
def search_page():
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute('SELECT hospital_id, hospital_name, city FROM hospitals')
    hospitals = cursor.fetchall()
    return render_template('search/search.html', hospitals=hospitals)

@search_bp.route('/results')
def search_results():
    blood_type = request.args.get('blood_type')
    location = request.args.get('location')
    hospital_id = request.args.get('hospital_id')
    
    query = '''
        SELECT bi.blood_type, bi.units, bi.collection_date, bi.expiry_date,
               h.hospital_id, h.hospital_name, h.address, h.city, h.phone, h.email,
               h.emergency_contact, h.operating_hours
        FROM blood_inventory bi
        JOIN hospitals h ON bi.hospital_id = h.hospital_id
        WHERE bi.units > 0
    '''
    params = []
    
    if blood_type:
        query += ' AND bi.blood_type = %s'
        params.append(blood_type)
    
    if hospital_id:
        query += ' AND h.hospital_id = %s'
        params.append(hospital_id)
    elif location:
        query += ' AND (h.address LIKE %s OR h.hospital_name LIKE %s OR h.city LIKE %s)'
        location_param = f'%{location}%'
        params.extend([location_param] * 3)
    
    query += ' ORDER BY bi.units DESC, bi.expiry_date ASC'
    
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute(query, params)
    results = cursor.fetchall()
    
    return render_template('search/results.html', results=results)

@search_bp.route('/api/blood-availability')
def api_blood_availability():
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute('''
        SELECT blood_type, SUM(units) as total_units
        FROM blood_inventory
        GROUP BY blood_type
        ORDER BY blood_type
    ''')
    results = cursor.fetchall()
    
    availability = {}
    for result in results:
        availability[result['blood_type']] = result['total_units']
    
    return jsonify({
        'status': 'success',
        'data': availability
    })

@search_bp.route('/emergency-request', methods=['GET', 'POST'])
def emergency_request():
    if request.method == 'POST':
        if request.is_json:
            data = request.json
            requester_name = data.get('requester_name')
            requester_contact = data.get('requester_contact')
            patient_name = data.get('patient_name')
            blood_type = data.get('blood_type')
            units = int(data.get('units')) if data.get('units') else None
            hospital = data.get('hospital')
            urgency = data.get('urgency')
            notes = data.get('notes')
        else:
            requester_name = request.form.get('requester_name')
            requester_contact = request.form.get('requester_contact')
            patient_name = request.form.get('patient_name')
            blood_type = request.form.get('blood_type')
            units = request.form.get('units', type=int)
            hospital = request.form.get('hospital')
            urgency = request.form.get('urgency')
            notes = request.form.get('notes')
        
        if not all([requester_name, requester_contact, patient_name, blood_type, units, hospital]):
            return jsonify({
                'status': 'error',
                'message': 'Please fill all required fields'
            }), 400
            
        if hospital is None:
            return jsonify({
                'status': 'error',
                'message': 'Hospital ID is required'
            }), 400
            
        try:
            hospital_id = int(str(hospital).strip())
            if hospital_id <= 0:
                raise ValueError("Hospital ID must be positive")
            hospital = hospital_id
        except (ValueError, TypeError, AttributeError):
            return jsonify({
                'status': 'error',
                'message': 'Invalid hospital ID'
            }), 400
        
        try:
            cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
            
            cursor.execute('''
                SELECT h.hospital_id, h.hospital_name, h.address, h.phone, bi.units
                FROM blood_inventory bi
                JOIN hospitals h ON bi.hospital_id = h.hospital_id
                WHERE bi.blood_type = %s AND bi.units >= %s
                ORDER BY 
                    CASE 
                        WHEN h.hospital_id = %s THEN 0 
                        ELSE 1 
                    END,
                    bi.units DESC
            ''', (blood_type, units, hospital))
            
            available_hospitals = cursor.fetchall()
            
            cursor.execute('''
                INSERT INTO blood_requests 
                (requester_name, requester_contact, patient_name, blood_type, 
                 units, hospital_id, urgency, notes, status, request_date) 
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, NOW())
            ''', (requester_name, requester_contact, patient_name, blood_type, 
                  units, hospital, urgency, notes, 'pending'))
            mysql.connection.commit()
            request_id = cursor.lastrowid
            
            if urgency in ['urgent', 'critical'] and (not available_hospitals or 
                available_hospitals[0]['hospital_id'] != hospital):
                cursor.execute('''
                    INSERT INTO emergency_notifications 
                    (request_id, hospital_id, status, created_at)
                    SELECT %s, hospital_id, 'pending', NOW()
                    FROM hospitals
                    WHERE hospital_id IN (
                        SELECT hospital_id 
                        FROM blood_inventory 
                        WHERE blood_type = %s AND units > 0
                    )
                ''', (request_id, blood_type))
                mysql.connection.commit()
            
            return jsonify({
                'status': 'success',
                'request_id': request_id,
                'available_hospitals': available_hospitals
            })
        except Exception as e:
            mysql.connection.rollback()
            return jsonify({
                'status': 'error',
                'message': 'An error occurred while processing your request'
            }), 500
    
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute('''
        SELECT h.hospital_id, h.hospital_name, 
               GROUP_CONCAT(
                   CONCAT(bi.blood_type, ': ', bi.units) 
                   SEPARATOR ', '
               ) as available_blood
        FROM hospitals h
        LEFT JOIN blood_inventory bi ON h.hospital_id = bi.hospital_id
        WHERE bi.units > 0
        GROUP BY h.hospital_id
        ORDER BY h.hospital_name
    ''')
    hospitals = cursor.fetchall()
    
    return render_template('search/emergency_request.html', 
                         hospitals=hospitals)

@search_bp.route('/request-status/<int:request_id>')
def request_status(request_id):
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute('SELECT * FROM blood_requests WHERE request_id = %s', (request_id,))
    request_data = cursor.fetchone()
    
    if not request_data:
        return render_template('search/request_status.html', error='Request not found')
    
    return render_template('search/request_status.html', request=request_data)

@search_bp.route('/compatibility')
def compatibility_chart():
    return render_template('search/compatibility.html')

@search_bp.route('/locations')
def donation_locations():
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute('SELECT * FROM hospitals ORDER BY hospital_name')
    locations = cursor.fetchall()
    
    return render_template('search/locations.html', locations=locations)