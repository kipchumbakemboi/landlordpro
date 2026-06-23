-- =========================================================
-- LANDLORDPRO FINAL DATABASE SCHEMA
-- Source of truth for production database setup
-- Updated: 2026-06-23
-- Target: MySQL 8+
-- =========================================================

CREATE DATABASE IF NOT EXISTS landlordpro
  CHARACTER SET utf8mb4
  COLLATE utf8mb4_unicode_ci;

USE landlordpro;

-- Drop tables in dependency order when rebuilding from scratch.
-- WARNING: Uncomment only if you intentionally want to reset the database.
-- DROP TABLE IF EXISTS notifications;
-- DROP TABLE IF EXISTS messages;
-- DROP TABLE IF EXISTS invoices;
-- DROP TABLE IF EXISTS repairs;
-- DROP TABLE IF EXISTS payments;
-- DROP TABLE IF EXISTS tenants;
-- DROP TABLE IF EXISTS units;
-- DROP TABLE IF EXISTS properties;
-- DROP TABLE IF EXISTS users;

-- =========================================================
-- 1. USERS
-- Stores landlords and tenants login accounts.
-- =========================================================
CREATE TABLE IF NOT EXISTS users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    fullname VARCHAR(255) NOT NULL,
    email VARCHAR(255) NOT NULL UNIQUE,
    phone VARCHAR(30),
    password_hash TEXT NOT NULL,
    role ENUM('landlord', 'tenant') NOT NULL DEFAULT 'tenant',
    two_factor_enabled BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,

    INDEX idx_users_email (email),
    INDEX idx_users_role (role)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- =========================================================
-- 2. PROPERTIES
-- Properties/apartments owned by landlords.
-- =========================================================
CREATE TABLE IF NOT EXISTS properties (
    id INT AUTO_INCREMENT PRIMARY KEY,
    landlord_id INT NOT NULL,
    property_name VARCHAR(255) NOT NULL,
    location VARCHAR(255),
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT fk_properties_landlord
        FOREIGN KEY (landlord_id) REFERENCES users(id)
        ON DELETE CASCADE,

    INDEX idx_properties_landlord_id (landlord_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- =========================================================
-- 3. UNITS
-- Houses/units belonging to properties.
-- =========================================================
CREATE TABLE IF NOT EXISTS units (
    id INT AUTO_INCREMENT PRIMARY KEY,
    property_id INT NOT NULL,
    unit_number VARCHAR(50) NOT NULL,
    rent_amount DECIMAL(10,2) NOT NULL DEFAULT 0.00,
    due_day INT NOT NULL DEFAULT 5,
    late_fee_percent DECIMAL(5,2) NOT NULL DEFAULT 5.00,
    status ENUM('occupied', 'vacant', 'repair') NOT NULL DEFAULT 'vacant',
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT fk_units_property
        FOREIGN KEY (property_id) REFERENCES properties(id)
        ON DELETE CASCADE,

    UNIQUE KEY uq_units_property_unit_number (property_id, unit_number),
    INDEX idx_units_property_id (property_id),
    INDEX idx_units_status (status)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- =========================================================
-- 4. TENANTS
-- Tenant profile details and lease information.
-- Each tenant is linked to one user account.
-- Unit can be NULL before approval/assignment.
-- =========================================================
CREATE TABLE IF NOT EXISTS tenants (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL UNIQUE,
    unit_id INT NULL,
    id_number VARCHAR(50),
    occupation VARCHAR(120),
    emergency_contact VARCHAR(120),
    lease_start DATE,
    lease_end DATE,
    lease_document VARCHAR(255),
    approved BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT fk_tenants_user
        FOREIGN KEY (user_id) REFERENCES users(id)
        ON DELETE CASCADE,

    CONSTRAINT fk_tenants_unit
        FOREIGN KEY (unit_id) REFERENCES units(id)
        ON DELETE SET NULL,

    INDEX idx_tenants_unit_id (unit_id),
    INDEX idx_tenants_approved (approved),
    INDEX idx_tenants_lease_end (lease_end)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- =========================================================
-- 5. PAYMENTS
-- Rent payments and M-Pesa transaction records.
-- =========================================================
CREATE TABLE IF NOT EXISTS payments (
    id INT AUTO_INCREMENT PRIMARY KEY,
    tenant_id INT NOT NULL,
    unit_id INT NOT NULL,
    amount DECIMAL(10,2) NOT NULL,
    mpesa_receipt VARCHAR(255),
    payment_date DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    status VARCHAR(50) NOT NULL DEFAULT 'completed',
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT fk_payments_tenant
        FOREIGN KEY (tenant_id) REFERENCES tenants(id)
        ON DELETE CASCADE,

    CONSTRAINT fk_payments_unit
        FOREIGN KEY (unit_id) REFERENCES units(id)
        ON DELETE RESTRICT,

    INDEX idx_payments_tenant_id (tenant_id),
    INDEX idx_payments_unit_id (unit_id),
    INDEX idx_payments_payment_date (payment_date),
    INDEX idx_payments_status (status),
    INDEX idx_payments_mpesa_receipt (mpesa_receipt)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- =========================================================
-- 6. REPAIRS
-- Maintenance requests submitted by tenants.
-- =========================================================
CREATE TABLE IF NOT EXISTS repairs (
    id INT AUTO_INCREMENT PRIMARY KEY,
    tenant_id INT NOT NULL,
    title VARCHAR(255) NOT NULL,
    description TEXT,
    photo VARCHAR(255),
    priority ENUM('low', 'medium', 'high', 'urgent') NOT NULL DEFAULT 'medium',
    status ENUM('pending', 'approved', 'in_progress', 'completed') NOT NULL DEFAULT 'pending',
    landlord_note TEXT,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,

    CONSTRAINT fk_repairs_tenant
        FOREIGN KEY (tenant_id) REFERENCES tenants(id)
        ON DELETE CASCADE,

    INDEX idx_repairs_tenant_id (tenant_id),
    INDEX idx_repairs_priority (priority),
    INDEX idx_repairs_status (status),
    INDEX idx_repairs_created_at (created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- =========================================================
-- 7. INVOICES
-- Generated PDF invoice records for rent and repairs.
-- =========================================================
CREATE TABLE IF NOT EXISTS invoices (
    id INT AUTO_INCREMENT PRIMARY KEY,
    tenant_id INT NOT NULL,
    amount DECIMAL(10,2) NOT NULL DEFAULT 0.00,
    invoice_type ENUM('rent', 'repair') NOT NULL DEFAULT 'rent',
    pdf_path VARCHAR(255),
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT fk_invoices_tenant
        FOREIGN KEY (tenant_id) REFERENCES tenants(id)
        ON DELETE CASCADE,

    INDEX idx_invoices_tenant_id (tenant_id),
    INDEX idx_invoices_type (invoice_type),
    INDEX idx_invoices_created_at (created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- =========================================================
-- 8. MESSAGES
-- In-app landlord/tenant chat messages.
-- =========================================================
CREATE TABLE IF NOT EXISTS messages (
    id INT AUTO_INCREMENT PRIMARY KEY,
    sender_id INT NOT NULL,
    receiver_id INT NOT NULL,
    content TEXT NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    read_at DATETIME NULL,

    CONSTRAINT fk_messages_sender
        FOREIGN KEY (sender_id) REFERENCES users(id)
        ON DELETE CASCADE,

    CONSTRAINT fk_messages_receiver
        FOREIGN KEY (receiver_id) REFERENCES users(id)
        ON DELETE CASCADE,

    INDEX idx_messages_sender_id (sender_id),
    INDEX idx_messages_receiver_id (receiver_id),
    INDEX idx_messages_created_at (created_at),
    INDEX idx_messages_conversation (sender_id, receiver_id, created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- =========================================================
-- 9. NOTIFICATIONS
-- In-app notifications for reminders, repairs, approvals, etc.
-- =========================================================
CREATE TABLE IF NOT EXISTS notifications (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    title VARCHAR(255) NOT NULL,
    body TEXT,
    is_read BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT fk_notifications_user
        FOREIGN KEY (user_id) REFERENCES users(id)
        ON DELETE CASCADE,

    INDEX idx_notifications_user_id (user_id),
    INDEX idx_notifications_is_read (is_read),
    INDEX idx_notifications_created_at (created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- =========================================================
-- END OF FINAL LANDLORDPRO DATABASE SCHEMA
-- =========================================================
