from flask import Flask, render_template, request, jsonify, session
from flask_mysqldb import MySQL
from config.config import Config

app = Flask(__name__)

# Configure MySQL from config file
app.config.from_object(Config)

# Initialize MySQL
mysql = MySQL(app)

# Import routes after app initialization to avoid circular imports
from controllers.auth_controller import auth_bp, init_db as auth_init_db
from controllers.donor_controller import donor_bp
from controllers.management_controller import management_bp, init_db as management_init_db
from controllers.search_controller import search_bp, init_db as search_init_db

# Register blueprints
app.register_blueprint(auth_bp)
app.register_blueprint(donor_bp)
app.register_blueprint(management_bp)
app.register_blueprint(search_bp)

# Create application context
with app.app_context():
    # Initialize database connections
    auth_init_db(mysql)
    management_init_db(mysql)
    search_init_db(mysql)
    
    # Initialize donor controller database
    from controllers.donor_controller import init_db as donor_init_db
    donor_init_db(mysql)

@app.route('/')
def index():
    return render_template('index.html')

if __name__ == '__main__':
    app.run(debug=True)