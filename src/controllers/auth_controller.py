from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from werkzeug.security import generate_password_hash, check_password_hash
from flask_mysqldb import MySQL
import MySQLdb.cursors

auth_bp = Blueprint('auth', __name__, url_prefix='/auth')
mysql = None

def init_db(db_instance):
    global mysql
    if db_instance and hasattr(db_instance, 'connection'):
        mysql = db_instance
    else:
        raise ValueError("Invalid MySQL instance provided")

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if 'logged_in' in session:
        return redirect(url_for('index'))
    
    if 'login_message' in session:
        flash(session.pop('login_message'), 'success')
    
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cursor.execute('SELECT * FROM users WHERE username = %s', (username,))
        user = cursor.fetchone()
        
        if user and check_password_hash(user['password'], password):
            session['logged_in'] = True
            session['id'] = user['id']
            session['username'] = user['username']
            session['role'] = user['role']
            session['hospital_id'] = user['hospital_id']
            
            if user['role'] == 'donor_staff':
                return redirect(url_for('donor.dashboard'))
            elif user['role'] == 'management_staff':
                return redirect(url_for('management.dashboard'))
            else:
                return redirect(url_for('index'))
        else:
            flash('Incorrect username/password!', 'danger')
    
    return render_template('auth/login.html')

@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    if 'logged_in' in session:
        return redirect(url_for('index'))
    
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        email = request.form['email']
        role = request.form['role']
        
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cursor.execute('SELECT * FROM users WHERE username = %s OR email = %s', (username, email))
        user = cursor.fetchone()
        
        if user:
            flash('Account already exists!', 'danger')
        elif not username or not password or not email:
            flash('Please fill out the form!', 'danger')
        else:
            hashed_password = generate_password_hash(password)
            
            cursor.execute('INSERT INTO users (username, password, email, role) VALUES (%s, %s, %s, %s)',
                          (username, hashed_password, email, role))
            mysql.connection.commit()
            
            flash('You have successfully registered! You can now login.', 'success')
            return redirect(url_for('auth.login'))
    
    return render_template('auth/register.html')

@auth_bp.route('/register/hospital', methods=['GET', 'POST'])
def register_hospital():
    if 'logged_in' in session:
        return redirect(url_for('index'))
    
    if request.method == 'POST':
        hospital_name = request.form['hospital_name']
        address = request.form['address']
        city = request.form['city']
        phone = request.form['phone']
        email = request.form.get('email')
        emergency_contact = request.form.get('emergency_contact')
        operating_hours = request.form.get('operating_hours')
        username = request.form['username']
        password = request.form['password']
        
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cursor.execute('SELECT * FROM users WHERE username = %s OR email = %s', (username, email))
        existing_user = cursor.fetchone()
        
        if existing_user:
            flash('Username or email already exists!', 'danger')
            return render_template('auth/hospital_register.html')
        
        try:
            cursor.execute('INSERT INTO hospitals (hospital_name, address, city, phone, email, emergency_contact, operating_hours) VALUES (%s, %s, %s, %s, %s, %s, %s)',
                          (hospital_name, address, city, phone, email, emergency_contact, operating_hours))
            mysql.connection.commit()
            
            hospital_id = cursor.lastrowid
            
            hashed_password = generate_password_hash(password)
            cursor.execute('INSERT INTO users (username, password, email, role, hospital_id) VALUES (%s, %s, %s, %s, %s)',
                          (username, hashed_password, email, 'management_staff', hospital_id))
            mysql.connection.commit()
            
            session['new_hospital_id'] = hospital_id
            session['temp_success_message'] = 'Hospital registered successfully! Please set up your initial inventory.'
            return redirect(url_for('auth.setup_initial_inventory'))
        except Exception as e:
            mysql.connection.rollback()
            flash('An error occurred during registration.', 'error')
            return render_template('auth/hospital_register.html')
    
    return render_template('auth/hospital_register.html')

@auth_bp.route('/setup_initial_inventory', methods=['GET', 'POST'])
def setup_initial_inventory():
    hospital_id = session.get('new_hospital_id')
    if not hospital_id:
        flash('Please register your hospital first.', 'error')
        return redirect(url_for('auth.register_hospital'))
    
    success_message = session.pop('temp_success_message', None)
    if success_message:
        flash(success_message, 'success')

    if request.method == 'POST':
        try:
            cursor = mysql.connection.cursor()
            blood_types = ['A+', 'A-', 'B+', 'B-', 'AB+', 'AB-', 'O+', 'O-']
            for blood_type in blood_types:
                units = int(request.form.get(blood_type, 0))
                cursor.execute('INSERT INTO blood_inventory (hospital_id, blood_type, units) VALUES (%s, %s, %s)',
                              (hospital_id, blood_type, units))
            mysql.connection.commit()
            
            session['login_message'] = 'Initial inventory setup completed successfully! You can now login.'
            session.pop('new_hospital_id', None)
            return redirect(url_for('auth.login'))

        except Exception as e:
            mysql.connection.rollback()
            flash('An error occurred while setting up the inventory.', 'error')
            print(f"Error: {e}")
            return redirect(url_for('auth.setup_initial_inventory'))

    return render_template('auth/initial_inventory.html')

@auth_bp.route('/logout')
def logout():
    session.pop('logged_in', None)
    session.pop('id', None)
    session.pop('username', None)
    session.pop('role', None)
    
    return redirect(url_for('index'))