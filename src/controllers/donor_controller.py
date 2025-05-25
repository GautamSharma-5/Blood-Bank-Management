from flask import Blueprint, render_template, request, redirect, url_for, flash, session, jsonify
from flask_mysqldb import MySQL
import MySQLdb.cursors
from datetime import datetime, timedelta

donor_bp = Blueprint('donor', __name__, url_prefix='/donor')

mysql = None

def init_db(db_instance):
    global mysql
    mysql = db_instance

def donor_staff_required(f):
    def decorated_function(*args, **kwargs):
        if 'logged_in' not in session or session.get('role') != 'donor_staff':
            flash('You need to be logged in as donor staff to access this page', 'danger')
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    decorated_function.__name__ = f.__name__
    return decorated_function

@donor_bp.route('/dashboard')
@donor_staff_required
def dashboard():
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    
    cursor.execute('SELECT COUNT(*) as total_donors FROM donors')
    total_donors = cursor.fetchone()['total_donors']
    
    cursor.execute('SELECT COUNT(*) as recent_donations FROM donations WHERE donation_date >= DATE_SUB(CURDATE(), INTERVAL 30 DAY)')
    recent_donations = cursor.fetchone()['recent_donations']
    
    cursor.execute('SELECT blood_type, COUNT(*) as count FROM donors GROUP BY blood_type')
    blood_type_data = cursor.fetchall()
    
    cursor.execute('''
        SELECT d.donation_id, d.donor_id, CONCAT(dn.first_name, ' ', dn.last_name) as name, d.donation_date, d.units, d.blood_type 
        FROM donations d 
        JOIN donors dn ON d.donor_id = dn.donor_id 
        ORDER BY d.donation_date DESC LIMIT 5
    ''')
    recent_donation_list = cursor.fetchall()
    
    return render_template('donor/dashboard.html', 
                           total_donors=total_donors,
                           recent_donations=recent_donations,
                           blood_type_data=blood_type_data,
                           recent_donation_list=recent_donation_list)

@donor_bp.route('/donors')
@donor_staff_required
def list_donors():
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute('''
        SELECT d.*, 
               (SELECT COUNT(*) FROM donations WHERE donor_id = d.donor_id) as donation_count,
               (SELECT MAX(donation_date) FROM donations WHERE donor_id = d.donor_id) as last_donation
        FROM donors d
        ORDER BY d.last_name, d.first_name
    ''')
    donors = cursor.fetchall()
    
    return render_template('donor/donors.html', donors=donors)

@donor_bp.route('/donors/add', methods=['GET', 'POST'])
@donor_staff_required
def add_donor():
    if request.method == 'POST':
        first_name = request.form['first_name']
        last_name = request.form['last_name']
        date_of_birth = request.form['date_of_birth']
        gender = request.form['gender']
        blood_type = request.form['blood_type']
        phone = request.form['phone']
        email = request.form['email']
        address = request.form['address']
        weight = request.form['weight']
        medical_conditions = request.form['medical_conditions']
        medications = request.form['medications']
        
        if not first_name or not last_name or not date_of_birth or not blood_type or not phone:
            flash('Please fill all required fields', 'danger')
            return redirect(url_for('donor.add_donor'))
        
        cursor = mysql.connection.cursor()
        cursor.execute('''
            INSERT INTO donors 
            (first_name, last_name, date_of_birth, gender, blood_type, phone, email, address, weight, medical_conditions, medications, created_at) 
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NOW())
        ''', (first_name, last_name, date_of_birth, gender, blood_type, phone, email, address, weight, medical_conditions, medications))
        mysql.connection.commit()
        
        flash('Donor added successfully', 'success')
        return redirect(url_for('donor.list_donors'))
    
    return render_template('donor/add_donor.html')

@donor_bp.route('/donors/<int:donor_id>')
@donor_staff_required
def view_donor(donor_id):
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute('''
        SELECT d.*,
               ld.donation_date as last_donation_date
        FROM donors d
        LEFT JOIN (
            SELECT donor_id, donation_date,
                   ROW_NUMBER() OVER (PARTITION BY donor_id ORDER BY donation_date DESC) as rn
            FROM donations
        ) ld ON d.donor_id = ld.donor_id AND ld.rn = 1
        WHERE d.donor_id = %s
    ''', (donor_id,))
    donor = cursor.fetchone()
    
    if not donor:
        flash('Donor not found', 'danger')
        return redirect(url_for('donor.list_donors'))
    
    cursor.execute('SELECT * FROM donations WHERE donor_id = %s ORDER BY donation_date DESC', (donor_id,))
    donations = cursor.fetchall()
    
    return render_template('donor/view_donor.html', donor=donor, donations=donations)

@donor_bp.route('/donors/<int:donor_id>/edit', methods=['GET', 'POST'])
@donor_staff_required
def edit_donor(donor_id):
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute('SELECT * FROM donors WHERE donor_id = %s', (donor_id,))
    donor = cursor.fetchone()
    
    if not donor:
        flash('Donor not found', 'danger')
        return redirect(url_for('donor.list_donors'))
    
    if request.method == 'POST':
        first_name = request.form['first_name']
        last_name = request.form['last_name']
        date_of_birth = request.form['date_of_birth']
        gender = request.form['gender']
        blood_type = request.form['blood_type']
        phone = request.form['phone']
        email = request.form['email']
        address = request.form['address']
        weight = request.form['weight']
        medical_conditions = request.form['medical_conditions']
        medications = request.form['medications']
        
        if not first_name or not last_name or not date_of_birth or not blood_type or not phone:
            flash('Please fill all required fields', 'danger')
            return redirect(url_for('donor.edit_donor', donor_id=donor_id))
        
        cursor.execute('''
            UPDATE donors SET 
            first_name = %s, last_name = %s, date_of_birth = %s, gender = %s, 
            blood_type = %s, phone = %s, email = %s, address = %s,
            weight = %s, medical_conditions = %s, medications = %s
            WHERE donor_id = %s
        ''', (first_name, last_name, date_of_birth, gender, blood_type, phone, email, address, 
              weight, medical_conditions, medications, donor_id))
        mysql.connection.commit()
        
        flash('Donor updated successfully', 'success')
        return redirect(url_for('donor.view_donor', donor_id=donor_id))
    
    return render_template('donor/edit_donor.html', donor=donor)

@donor_bp.route('/donations')
@donor_staff_required
def list_donations():
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute('''
        SELECT d.*, dn.first_name, dn.last_name, dn.blood_type 
        FROM donations d 
        JOIN donors dn ON d.donor_id = dn.donor_id 
        ORDER BY d.donation_date DESC
    ''')
    donations = cursor.fetchall()
    
    return render_template('donor/donations.html', donations=donations)

@donor_bp.route('/donations/add', methods=['GET', 'POST'])
@donor_staff_required
def add_donation():
    if request.method == 'POST':
        donor_id = request.form['donor_id']
        donation_date = request.form.get('donation_date', datetime.now().strftime('%Y-%m-%d'))
        units = request.form.get('units', 1)
        hemoglobin = request.form.get('hemoglobin')
        blood_pressure = request.form.get('blood_pressure')
        pulse = request.form.get('pulse')
        notes = request.form.get('notes')
        
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cursor.execute('SELECT blood_type FROM donors WHERE donor_id = %s', (donor_id,))
        donor = cursor.fetchone()
        
        if not donor:
            flash('Donor not found', 'danger')
            return redirect(url_for('donor.add_donation'))
        
        blood_type = donor['blood_type']
        
        cursor.execute('''
            INSERT INTO donations 
            (donor_id, donation_date, units, blood_type, notes, status, weight, medical_conditions, medications) 
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        ''', (donor_id, donation_date, units, blood_type, notes, 'approved', request.form.get('weight'), request.form.get('medical_conditions'), request.form.get('medications')))
        mysql.connection.commit()
        
        cursor.execute('SELECT * FROM blood_inventory WHERE blood_type = %s', (blood_type,))
        inventory = cursor.fetchone()
        
        if inventory:
            cursor.execute('UPDATE blood_inventory SET units = units + %s WHERE blood_type = %s', 
                          (units, blood_type))
        else:
            cursor.execute('INSERT INTO blood_inventory (blood_type, units) VALUES (%s, %s)', 
                          (blood_type, units))
        
        cursor.execute('UPDATE donors SET last_donation_date = %s WHERE donor_id = %s', 
                      (donation_date, donor_id))
        
        mysql.connection.commit()
        
        flash('Donation recorded successfully', 'success')
        return redirect(url_for('donor.list_donations'))
    
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute('SELECT donor_id, first_name, last_name, blood_type FROM donors ORDER BY last_name, first_name')
    donors = cursor.fetchall()
    
    return render_template('donor/add_donation.html', donors=donors, today=datetime.now().strftime('%Y-%m-%d'))

@donor_bp.route('/donations/<int:donation_id>')
@donor_staff_required
def view_donation(donation_id):
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute('''
        SELECT d.*, dn.first_name, dn.last_name, dn.blood_type, dn.phone, dn.email 
        FROM donations d 
        JOIN donors dn ON d.donor_id = dn.donor_id 
        WHERE d.donation_id = %s
    ''', (donation_id,))
    donation = cursor.fetchone()
    
    if not donation:
        flash('Donation not found', 'danger')
        return redirect(url_for('donor.list_donations'))
    
    return render_template('donor/view_donation.html', donation=donation)

@donor_bp.route('/eligibility')
@donor_staff_required
def check_eligibility():
    return render_template('donor/eligibility.html')

@donor_bp.route('/api/check-eligibility', methods=['POST'])
def api_check_eligibility():
    data = request.get_json()
    donor_id = data.get('donor_id')
    
    if not donor_id:
        return jsonify({'error': 'Donor ID is required'}), 400
    
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute('''
        SELECT d.*, 
               (SELECT MAX(donation_date) FROM donations WHERE donor_id = d.donor_id) as last_donation
        FROM donors d
        WHERE d.donor_id = %s
    ''', (donor_id,))
    donor = cursor.fetchone()
    
    if not donor:
        return jsonify({'error': 'Donor not found'}), 404
    
    result = {
        'eligible': True,
        'reasons': [],
        'next_eligible_date': None
    }
    
    if donor['last_donation']:
        last_donation = donor['last_donation']
        today = datetime.now().date()
        days_since_last = (today - last_donation.date()).days
        
        if days_since_last < 56:
            result['eligible'] = False
            result['reasons'].append(f'Last donation was only {days_since_last} days ago')
            next_eligible = last_donation.date() + timedelta(days=56)
            result['next_eligible_date'] = next_eligible.strftime('%Y-%m-%d')
    
    return jsonify(result)

@donor_bp.route('/reports')
@donor_staff_required
def reports():
    return render_template('donor/reports.html')

@donor_bp.route('/api/reports/donations-by-month', methods=['GET'])
def api_donations_by_month():
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute('''
        SELECT MONTH(donation_date) as month, COUNT(*) as count, SUM(units) as units
        FROM donations
        WHERE YEAR(donation_date) = YEAR(CURDATE())
        GROUP BY MONTH(donation_date)
        ORDER BY month
    ''')
    data = cursor.fetchall()
    
    months = ['January', 'February', 'March', 'April', 'May', 'June', 
              'July', 'August', 'September', 'October', 'November', 'December']
    
    counts = [0] * 12
    units = [0] * 12
    
    for item in data:
        month_index = item['month'] - 1  # Adjust for 0-based index
        counts[month_index] = item['count']
        units[month_index] = item['units']
@donor_bp.route('/register', methods=['GET', 'POST'])
def register_donor():
    if request.method == 'POST':
        name = request.form['name']
        date_of_birth = request.form['date_of_birth']
        gender = request.form['gender']
        blood_type = request.form['blood_type']
        phone = request.form['phone']
        email = request.form.get('email', '')
        address = request.form.get('address', '')
        medical_conditions = request.form.get('medical_conditions', '')
        
        name_parts = name.split(' ', 1)
        first_name = name_parts[0]
        last_name = name_parts[1] if len(name_parts) > 1 else ''
        
        if not name or not date_of_birth or not blood_type or not phone:
            flash('Please fill all required fields', 'danger')
            return redirect(url_for('donor.register_donor'))
        
        cursor = mysql.connection.cursor()
        cursor.execute('''
            INSERT INTO donors 
            (first_name, last_name, date_of_birth, gender, blood_type, phone, email, address, medical_notes, registration_date) 
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        ''', (first_name, last_name, date_of_birth, gender, blood_type, phone, email, address, medical_conditions, datetime.now()))
        mysql.connection.commit()
        
        flash('Thank you for registering as a donor!', 'success')
        return redirect(url_for('index'))
    
    return render_template('donor/register.html')