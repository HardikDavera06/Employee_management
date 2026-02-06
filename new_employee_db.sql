-- phpMyAdmin SQL Dump
-- version 5.2.1
-- https://www.phpmyadmin.net/
--
-- Host: 127.0.0.1
-- Generation Time: Feb 06, 2026 at 04:42 PM
-- Server version: 10.4.32-MariaDB
-- PHP Version: 8.2.12

SET SQL_MODE = "NO_AUTO_VALUE_ON_ZERO";
START TRANSACTION;
SET time_zone = "+00:00";


/*!40101 SET @OLD_CHARACTER_SET_CLIENT=@@CHARACTER_SET_CLIENT */;
/*!40101 SET @OLD_CHARACTER_SET_RESULTS=@@CHARACTER_SET_RESULTS */;
/*!40101 SET @OLD_COLLATION_CONNECTION=@@COLLATION_CONNECTION */;
/*!40101 SET NAMES utf8mb4 */;

--
-- Database: `employee_db`
--

-- --------------------------------------------------------

--
-- Table structure for table `employees`
--

CREATE TABLE `employees` (
  `id` varchar(64) NOT NULL,
  `name` varchar(255) NOT NULL,
  `email` varchar(255) NOT NULL,
  `phone` varchar(32) DEFAULT NULL,
  `department` varchar(64) DEFAULT NULL,
  `role` varchar(32) NOT NULL,
  `password` varchar(255) NOT NULL,
  `salary` double DEFAULT 0
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

--
-- Dumping data for table `employees`
--

INSERT INTO `employees` (`id`, `name`, `email`, `phone`, `department`, `role`, `password`, `salary`) VALUES
('EMP001', 'Admin', 'admin@gmail.com', '0123456789', 'Finance', 'admin', '240be518fabd2724ddb6f04eeb1da5967448d7e831c08c8fa822809f74c720a9', 30000),
('EMP002', 'First', 'first@gmail.com', '1111111111', 'Human Resources', 'employee', 'a665a45920422f9d417e4867efdc4fb8a04a1f3fff1fa07e998e86f7f7a27ae3', 60000),
('EMP003', 'hardik', 'daverahardik43@gmail.com', '1111101111', 'Human Resources', 'employee', 'be47addbcb8f60566a3d7fd5a36f8195798e2848b368195d9a5d20e007c59a0c', 60000);

-- --------------------------------------------------------

--
-- Table structure for table `leaves`
--

CREATE TABLE `leaves` (
  `id` varchar(64) NOT NULL,
  `emp_id` varchar(64) NOT NULL,
  `emp_name` varchar(255) NOT NULL,
  `leave_type` varchar(64) NOT NULL,
  `start_date` date NOT NULL,
  `end_date` date NOT NULL,
  `reason` text DEFAULT NULL,
  `status` varchar(32) NOT NULL,
  `applied_date` datetime NOT NULL,
  `duration_type` varchar(32) DEFAULT 'Full Day'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

--
-- Dumping data for table `leaves`
--

INSERT INTO `leaves` (`id`, `emp_id`, `emp_name`, `leave_type`, `start_date`, `end_date`, `reason`, `status`, `applied_date`, `duration_type`) VALUES
('LV001', 'EMP002', 'first', 'Sick Leave', '2025-11-26', '2025-11-26', ' jh', 'Rejected', '2025-11-26 23:07:27', 'Full Day'),
('LV002', 'EMP002', 'first', 'Sick Leave', '2025-11-27', '2025-11-27', 'kbhvj', 'Approved', '2025-11-27 23:10:03', 'Full Day'),
('LV003', 'EMP002', 'first', 'Sick Leave', '2025-11-27', '2025-11-27', 'kjb', 'Approved', '2025-11-27 23:11:43', 'Half Day'),
('LV004', 'EMP002', 'first', 'Sick Leave', '2025-11-28', '2025-11-28', 'sfd', 'Approved', '2025-11-28 20:19:55', 'Full Day'),
('LV005', 'EMP002', 'first', 'Casual Leave', '2026-01-29', '2026-01-29', 'hghfg8', 'Approved', '2026-01-29 20:49:08', 'Half Day'),
('LV006', 'EMP002', 'first', 'Sick Leave', '2026-02-02', '2026-02-04', 'dsf', 'Approved', '2026-01-29 20:51:52', 'Full Day'),
('LV007', 'EMP004', 'Testing ', 'Sick Leave', '2026-02-01', '2026-02-01', 'asfassa', 'Pending', '2026-02-01 11:57:40', 'Full Day');

-- --------------------------------------------------------

--
-- Table structure for table `payroll_records`
--

CREATE TABLE `payroll_records` (
  `id` varchar(64) NOT NULL,
  `emp_id` varchar(64) NOT NULL,
  `month` varchar(7) NOT NULL,
  `base_salary` double NOT NULL,
  `overtime_hours` double DEFAULT 0,
  `overtime_rate` double DEFAULT 0,
  `bonus` double DEFAULT 0,
  `other_deductions` double DEFAULT 0,
  `leave_deduction` double DEFAULT 0,
  `net_salary` double NOT NULL,
  `generated_on` datetime NOT NULL,
  `slip_path` varchar(255) DEFAULT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

--
-- Dumping data for table `payroll_records`
--

INSERT INTO `payroll_records` (`id`, `emp_id`, `month`, `base_salary`, `overtime_hours`, `overtime_rate`, `bonus`, `other_deductions`, `leave_deduction`, `net_salary`, `generated_on`, `slip_path`) VALUES
('PAY0001', 'EMP002', '2025-11', 10000, 10, 100, 10, 10, 0, 11000, '2025-11-27 21:41:11', 'salary_slips\\PAY0001_EMP002_2025-11.pdf'),
('PAY0002', 'EMP002', '2025-11', 10000, 0, 0, 0, 0, 333.3333333333333, 9666.666666666666, '2025-11-27 22:30:26', 'salary_slips\\PAY0002_EMP002_2025-11.pdf'),
('PAY0003', 'EMP002', '2025-11', 10000, 100, 100, 500, 100, 333.3333333333333, 20066.666666666668, '2025-11-27 22:47:31', 'salary_slips\\PAY0003_EMP002_2025-11.pdf'),
('PAY0004', 'EMP002', '2025-11', 10000, 10, 1, 5000, 1000, 333.3333333333333, 13676.666666666666, '2025-11-27 22:52:18', 'salary_slips\\PAY0004_EMP002_2025-11.pdf'),
('PAY0005', 'EMP002', '2025-11', 10000, 0, 0, 0, 0, 500, 9500, '2025-11-28 19:25:36', 'salary_slips\\PAY0005_EMP002_2025-11.pdf'),
('PAY0006', 'EMP002', '2026-01', 20000, 0, 100, 0, 1000, 0, 19000, '2026-01-29 19:29:54', 'salary_slips\\PAY0006_EMP002_2026-01.pdf'),
('PAY0007', 'EMP002', '2026-01', 20000, 0, 100, 0, 0, 0, 20000, '2026-01-29 19:32:50', 'salary_slips\\PAY0007_EMP002_2026-01.pdf');

-- --------------------------------------------------------

--
-- Table structure for table `salary_assignments`
--

CREATE TABLE `salary_assignments` (
  `id` varchar(64) NOT NULL,
  `emp_id` varchar(64) NOT NULL,
  `assigned_salary` double NOT NULL,
  `assigned_on` datetime NOT NULL,
  `assigned_by` varchar(64) DEFAULT NULL,
  `month` varchar(7) NOT NULL DEFAULT '0000-00',
  `bonus` decimal(12,2) DEFAULT 0.00
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

--
-- Dumping data for table `salary_assignments`
--

INSERT INTO `salary_assignments` (`id`, `emp_id`, `assigned_salary`, `assigned_on`, `assigned_by`, `month`, `bonus`) VALUES
('ASG0001', 'EMP002', 30516.13, '2026-01-30 21:22:19', 'EMP001', '2026-01', 1000.00),
('ASG0003', 'EMP004', 60100, '2026-01-30 22:32:16', 'EMP001', '2026-02', 100.00),
('ASG0004', 'EMP004', 60100, '2026-02-01 14:16:40', 'EMP001', '2026-03', 100.00),
('ASG0005', 'EMP004', 60000, '2026-02-01 14:17:04', 'EMP001', '2026-04', 0.00),
('ASG0006', 'EMP003', 60100, '2026-02-06 21:06:18', 'EMP001', '2026-02', 100.00);

-- --------------------------------------------------------

--
-- Table structure for table `salary_corrections`
--

CREATE TABLE `salary_corrections` (
  `id` varchar(64) NOT NULL,
  `emp_id` varchar(64) NOT NULL,
  `month` varchar(7) NOT NULL,
  `description` text DEFAULT NULL,
  `submitted_on` datetime NOT NULL,
  `status` varchar(32) NOT NULL,
  `assignment_id` varchar(64) DEFAULT NULL,
  `payroll_id` varchar(64) DEFAULT NULL,
  `admin_notes` text DEFAULT NULL,
  `rejection_reason` text DEFAULT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

--
-- Dumping data for table `salary_corrections`
--

INSERT INTO `salary_corrections` (`id`, `emp_id`, `month`, `description`, `submitted_on`, `status`, `assignment_id`, `payroll_id`, `admin_notes`, `rejection_reason`) VALUES
('REQ0001', 'EMP004', '2026-01', 'I got more 100 in my salary', '2026-01-31 21:52:05', 'Resolved', 'ASG0002', NULL, 'ok i changednit', NULL),
('REQ0002', 'EMP004', '2026-02', 'i got 900 less in my salary', '2026-02-01 11:43:09', 'Rejected', 'ASG0003', NULL, NULL, 'No, \nThis is right salary amount which i assigned you, \nalso i give you 100 more on your income'),
('REQ0003', 'EMP004', '2026-02', 'this is my requestxzxc', '2026-02-01 13:01:44', 'Withdrawn', NULL, NULL, NULL, NULL),
('REQ0004', 'EMP004', '2026-02', 'i want more', '2026-02-01 14:14:33', 'Pending', NULL, NULL, NULL, NULL),
('REQ0005', 'EMP004', '2026-02', 'check', '2026-02-01 14:23:20', 'Pending', NULL, NULL, NULL, NULL),
('REQ0006', 'EMP004', '2026-04', 'this check', '2026-02-01 14:38:16', 'Pending', 'ASG0005', NULL, NULL, NULL),
('REQ0007', 'EMP004', '2026-02', 'this is another check', '2026-02-01 14:38:36', 'Pending', NULL, NULL, NULL, NULL),
('REQ0008', 'EMP004', '2026-03', 'yes', '2026-02-01 14:38:54', 'Pending', NULL, NULL, NULL, NULL),
('REQ0009', 'EMP004', '2026-03', 'uhe', '2026-02-01 14:39:10', 'Pending', 'ASG0004', NULL, NULL, NULL),
('REQ0010', 'EMP004', '2026-04', 'bkjmbj', '2026-02-01 14:49:18', 'Pending', 'ASG0005', NULL, NULL, NULL),
('REQ0011', 'EMP003', '2026-02', 'THis is not valid', '2026-02-06 21:07:13', 'Pending', 'ASG0006', NULL, NULL, NULL);

--
-- Indexes for dumped tables
--

--
-- Indexes for table `employees`
--
ALTER TABLE `employees`
  ADD PRIMARY KEY (`id`);

--
-- Indexes for table `leaves`
--
ALTER TABLE `leaves`
  ADD PRIMARY KEY (`id`);

--
-- Indexes for table `payroll_records`
--
ALTER TABLE `payroll_records`
  ADD PRIMARY KEY (`id`);

--
-- Indexes for table `salary_assignments`
--
ALTER TABLE `salary_assignments`
  ADD PRIMARY KEY (`id`),
  ADD UNIQUE KEY `unique_emp_month` (`emp_id`,`month`);

--
-- Indexes for table `salary_corrections`
--
ALTER TABLE `salary_corrections`
  ADD PRIMARY KEY (`id`);
COMMIT;

/*!40101 SET CHARACTER_SET_CLIENT=@OLD_CHARACTER_SET_CLIENT */;
/*!40101 SET CHARACTER_SET_RESULTS=@OLD_CHARACTER_SET_RESULTS */;
/*!40101 SET COLLATION_CONNECTION=@OLD_COLLATION_CONNECTION */;
