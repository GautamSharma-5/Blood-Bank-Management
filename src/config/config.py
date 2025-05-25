class Config:
    # MySQL configurations
    MYSQL_HOST = 'localhost'
    MYSQL_USER = 'root'
    MYSQL_PASSWORD = ''
    MYSQL_DB = 'blood_bank'
    
    # Flask configurations
    SECRET_KEY = ''  # Updated to a secure random key
    
    # Session configurations
    PERMANENT_SESSION_LIFETIME = 1800  # 30 minutes session timeout