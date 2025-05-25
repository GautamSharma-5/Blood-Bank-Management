# Blood Bank Database System
A comprehensive web-based Blood Bank Management System that helps manage blood donations, inventory, and requests efficiently.

## Features
- **Donor Management**
  - Register and manage blood donors
  - Track donation history
  - Monitor donor eligibility

- **Blood Inventory Management**
  - Real-time blood unit tracking
  - Blood type distribution analytics
  - Inventory alerts and notifications

- **Request Management**
  - Process blood requests from hospitals
  - Track request status and fulfillment
  - Manage emergency requests

- **User Management**
  - Role-based access control (Donor Staff & Management Staff)
  - Secure authentication system
  - Hospital-specific user accounts

- **Analytics Dashboard**
  - Blood type distribution charts
  - Donation trends
  - Inventory status visualization

## Technology Stack
- **Backend**
  - Python Flask framework
  - MySQL Database
  - SQLAlchemy ORM

- **Frontend**
  - HTML5, CSS, JavaScript
  - Bootstrap for responsive design
  - Chart.js for data visualization

- **Security**
  - Password hashing
  - Session management
  - Role-based access control

## Installation
1. Clone the repository
   ```bash
   git clone https://github.com/GautamSharma-5/Blood-Bank-Management.git
   cd Blood-Bank-Management
   ```

2. Create a virtual environment
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. Install dependencies
   ```bash
   pip install -r requirements.txt
   ```

4. Set up the database
   - Create a MySQL database
   - Update database configuration in `src/config/config.py`
   - Run the initialization script:
     ```bash
     mysql -u your_username -p your_database < src/init_db.sql
     ```

5. Start the application
   ```bash
   python src/app.py
   ```

## Project Structure
```
src/
├── app.py                 # Application entry point
├── config/                # Configuration files
├── controllers/           # Route handlers
├── models/               # Database models
├── static/               # Static assets (CSS, JS)
├── templates/            # HTML templates
└── init_db.sql          # Database initialization script
```

## Usage
1. Access the application at `http://localhost:5000`
2. Log in with appropriate credentials based on role:
   - Donor Staff: Manage donors and donations
   - Management Staff: Handle inventory and requests

## Contributing
1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request

## Acknowledgments
- Bootstrap for the responsive UI components
- Chart.js for data visualization
- Flask community for the excellent web framework

## Generating a Secure Secret Key
To generate a secure secret key for your Flask application, you can use Python's `secrets` module. Here's how:

1. Open a Python terminal and run:
   ```python
   import secrets
   print(secrets.token_hex(16))  # Generates a 32-character hexadecimal secret key
   ```

2. Copy the generated key and update it in `src/config/config.py`:
   ```python
   SECRET_KEY = 'your-generated-key-here'
   ```

This ensures your application uses a cryptographically strong secret key for securing session data and other Flask features.
