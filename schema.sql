-- HR Chatbot Database Schema
CREATE DATABASE IF NOT EXISTS hr_chatbot;
USE hr_chatbot;

CREATE TABLE IF NOT EXISTS employees (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    employee_id VARCHAR(20) UNIQUE NOT NULL,
    password VARCHAR(255) NOT NULL,
    department VARCHAR(100),
    designation VARCHAR(100),
    project VARCHAR(150),
    manager_name VARCHAR(100),
    team_lead_name VARCHAR(100),
    annual_leave_balance INT DEFAULT 12,
    annual_leave_taken INT DEFAULT 0,
    sick_leave_balance INT DEFAULT 6,
    sick_leave_taken INT DEFAULT 0,
    lop_taken INT DEFAULT 0,
    joined_date DATE,
    contact_email VARCHAR(150),
    contact_phone VARCHAR(20),
    is_on_probation TINYINT(1) DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);

-- Sample employees
INSERT INTO employees (name, employee_id, password, department, designation, project, manager_name, team_lead_name,
    annual_leave_balance, annual_leave_taken, sick_leave_balance, sick_leave_taken, lop_taken,
    joined_date, contact_email, contact_phone, is_on_probation)
VALUES
    ('Arun Kumar', 'EMP001', 'pass123', 'Engineering', 'Software Engineer', 'Phoenix Platform',
     'Priya Sharma', 'Ravi Menon', 5, 7, 2, 4, 0, '2023-03-15', 'arun.kumar@company.com', '+91-9876543210', 0),
    ('Divya Nair', 'EMP002', 'pass456', 'Product', 'Product Manager', 'Horizon App',
     'Suresh Babu', 'Anitha R', 8, 4, 6, 0, 0, '2022-07-01', 'divya.nair@company.com', '+91-9123456789', 0),
    ('Karthik Rajan', 'EMP003', 'pass789', 'Design', 'UI/UX Designer', 'Nebula UI',
     'Priya Sharma', 'Divya Nair', 3, 9, 4, 2, 1, '2024-01-10', 'karthik.r@company.com', '+91-9988776655', 1);

-- Leave history table
CREATE TABLE IF NOT EXISTS leave_history (
    id INT AUTO_INCREMENT PRIMARY KEY,
    employee_id VARCHAR(20),
    leave_type ENUM('annual','sick','lop') NOT NULL,
    leave_date DATE DEFAULT (CURRENT_DATE),
    days INT DEFAULT 1,
    reason TEXT,
    status ENUM('pending','approved','rejected') DEFAULT 'pending',
    applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (employee_id) REFERENCES employees(employee_id)
);
