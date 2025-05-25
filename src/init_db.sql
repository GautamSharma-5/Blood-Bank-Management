-- Blood Bank Management System Database Initialization Script

USE blood_bank;

-- Hospitals table
CREATE TABLE IF NOT EXISTS hospitals (
    hospital_id INT AUTO_INCREMENT PRIMARY KEY,
    hospital_name VARCHAR(100) NOT NULL,
    address VARCHAR(255) NOT NULL,
    city VARCHAR(100) NOT NULL,
    phone VARCHAR(20) NOT NULL,
    email VARCHAR(100),
    emergency_contact VARCHAR(100),
    operating_hours VARCHAR(255),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Users table for authentication
CREATE TABLE IF NOT EXISTS users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(100) NOT NULL UNIQUE,
    password VARCHAR(255) NOT NULL,
    email VARCHAR(100) NOT NULL UNIQUE,
    role ENUM('donor_staff', 'management_staff') NOT NULL,
    hospital_id INT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (hospital_id) REFERENCES hospitals(hospital_id)
);

-- Donors table
CREATE TABLE IF NOT EXISTS donors (
    donor_id INT AUTO_INCREMENT PRIMARY KEY,
    first_name VARCHAR(50) NOT NULL,
    last_name VARCHAR(50) NOT NULL,
    blood_type ENUM('A+', 'A-', 'B+', 'B-', 'AB+', 'AB-', 'O+', 'O-') NOT NULL,
    phone VARCHAR(20) NOT NULL,
    email VARCHAR(100),
    address VARCHAR(255),
    date_of_birth DATE,
    gender ENUM('M', 'F', 'Other') NOT NULL,
    last_donation_date DATE,
    medical_history TEXT,
    weight DECIMAL(5,2),
    medical_conditions TEXT,
    medications TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Blood Inventory table
CREATE TABLE IF NOT EXISTS blood_inventory (
    inventory_id INT AUTO_INCREMENT PRIMARY KEY,
    blood_type ENUM('A+', 'A-', 'B+', 'B-', 'AB+', 'AB-', 'O+', 'O-') NOT NULL,
    units INT NOT NULL DEFAULT 0,
    hospital_id INT,
    collection_date DATE,
    expiry_date DATE,
    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    notes TEXT,
    FOREIGN KEY (hospital_id) REFERENCES hospitals(hospital_id),
    UNIQUE KEY (blood_type, hospital_id)
);

-- Blood Requests table
CREATE TABLE IF NOT EXISTS blood_requests (
    request_id INT AUTO_INCREMENT PRIMARY KEY,
    requester_name VARCHAR(100) NOT NULL,
    requester_contact VARCHAR(20) NOT NULL,
    patient_name VARCHAR(100),
    hospital_id INT NOT NULL,
    blood_type ENUM('A+', 'A-', 'B+', 'B-', 'AB+', 'AB-', 'O+', 'O-') NOT NULL,
    units INT NOT NULL,
    request_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    status ENUM('pending', 'approved', 'rejected', 'fulfilled') DEFAULT 'pending',
    notes TEXT,
    FOREIGN KEY (hospital_id) REFERENCES hospitals(hospital_id)
);

-- Donations table
CREATE TABLE IF NOT EXISTS donations (
    donation_id INT AUTO_INCREMENT PRIMARY KEY,
    donor_id INT NOT NULL,
    blood_type ENUM('A+', 'A-', 'B+', 'B-', 'AB+', 'AB-', 'O+', 'O-') NOT NULL,
    units INT NOT NULL DEFAULT 1,
    donation_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    hospital_id INT,
    status ENUM('pending', 'approved', 'rejected') DEFAULT 'pending',
    weight DECIMAL(5,2),
    medical_conditions TEXT,
    medications TEXT,
    notes TEXT,
    FOREIGN KEY (donor_id) REFERENCES donors(donor_id),
    FOREIGN KEY (hospital_id) REFERENCES hospitals(hospital_id)
);

-- Inventory Logs table
CREATE TABLE IF NOT EXISTS inventory_logs (
    log_id INT AUTO_INCREMENT PRIMARY KEY,
    blood_type ENUM('A+', 'A-', 'B+', 'B-', 'AB+', 'AB-', 'O+', 'O-') NOT NULL,
    previous_units INT NOT NULL,
    new_units INT NOT NULL,
    change_type ENUM('donation', 'request', 'expiry', 'adjustment', 'manual') NOT NULL,
    reference_id INT,
    user_id INT,
    updated_by VARCHAR(100),
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    notes TEXT,
    FOREIGN KEY (user_id) REFERENCES users(id)
);

-- Insert sample hospital management staff user
INSERT INTO users (username, password, email, role, hospital_id) VALUES
('hospital_admin', '$2b$12$1xxxxxxxxxxxxxxxxxxxxuZLbwxnpY0o58unSvIPxddLxGystU.', 'admin@citygeneral.com', 'management_staff', 1);

-- Insert sample hospital
INSERT INTO hospitals (hospital_name, address, city, phone, email, emergency_contact, operating_hours) VALUES
('City General Hospital', '123 Main Street', 'Cityville', '123-456-7890', 'info@citygeneral.com', 'Emergency: 911', 'Mon-Sun: 24 hours');

-- Blood Drive Events table
CREATE TABLE IF NOT EXISTS blood_drive_events (
    event_id INT AUTO_INCREMENT PRIMARY KEY,
    event_name VARCHAR(100) NOT NULL,
    description TEXT,
    location VARCHAR(255) NOT NULL,
    event_date DATE NOT NULL,
    start_time TIME NOT NULL,
    end_time TIME NOT NULL,
    hospital_id INT,
    organizer_name VARCHAR(100) NOT NULL,
    contact_phone VARCHAR(20) NOT NULL,
    contact_email VARCHAR(100),
    max_donors INT,
    registered_donors INT DEFAULT 0,
    status ENUM('upcoming', 'ongoing', 'completed', 'cancelled') DEFAULT 'upcoming',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (hospital_id) REFERENCES hospitals(hospital_id)
);

-- Blood Drive Registrations table
CREATE TABLE IF NOT EXISTS blood_drive_registrations (
    registration_id INT AUTO_INCREMENT PRIMARY KEY,
    event_id INT NOT NULL,
    donor_id INT NOT NULL,
    registration_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    status ENUM('registered', 'checked_in', 'completed', 'cancelled') DEFAULT 'registered',
    notes TEXT,
    FOREIGN KEY (event_id) REFERENCES blood_drive_events(event_id),
    FOREIGN KEY (donor_id) REFERENCES donors(donor_id)
);

-- Initialize blood inventory with zero units for all blood types
INSERT INTO blood_inventory (blood_type, units, hospital_id, collection_date, expiry_date) VALUES
('A+', 30, 1, CURDATE(), DATE_ADD(CURDATE(), INTERVAL 42 DAY)),
('A-', 10, 1, CURDATE(), DATE_ADD(CURDATE(), INTERVAL 42 DAY)),
('B+', 25, 1, CURDATE(), DATE_ADD(CURDATE(), INTERVAL 42 DAY)),
('B-', 8, 1, CURDATE(), DATE_ADD(CURDATE(), INTERVAL 42 DAY)),
('AB+', 15, 1, CURDATE(), DATE_ADD(CURDATE(), INTERVAL 42 DAY)),
('AB-', 5, 1, CURDATE(), DATE_ADD(CURDATE(), INTERVAL 42 DAY)),
('O+', 40, 1, CURDATE(), DATE_ADD(CURDATE(), INTERVAL 42 DAY)),
('O-', 20, 1, CURDATE(), DATE_ADD(CURDATE(), INTERVAL 42 DAY));