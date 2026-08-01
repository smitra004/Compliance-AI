import os
import csv
import random

BASE_DIR = "Evaluation"
DATASET_DIR = os.path.join(BASE_DIR, "dataset")

DEPARTMENTS = {
    "Finance": [
        "Quarterly Financial Report",
        "Budget Planning",
        "Expense Reimbursement",
        "Cash Flow Analysis",
        "Annual Financial Statement",
        "Tax Filing Guidelines",
        "Payroll Processing",
        "Capital Expenditure Approval",
        "Revenue Forecast",
        "Invoice Management",
        "Accounts Payable Review",
        "Accounts Receivable Summary",
        "Investment Portfolio Report",
        "Cost Optimization Plan",
        "Audit Preparation"
    ],

    "HR": [
        "Employee Leave Policy",
        "Performance Evaluation",
        "Recruitment Process",
        "Code of Conduct",
        "Employee Benefits",
        "Work From Home Policy",
        "Training Schedule",
        "Attendance Guidelines",
        "Grievance Resolution",
        "Promotion Criteria",
        "Exit Interview Process",
        "Employee Wellness Program",
        "Hiring Approval",
        "Diversity and Inclusion",
        "Onboarding Checklist"
    ],

    "Legal": [
        "Non Disclosure Agreement",
        "Service Agreement",
        "Vendor Contract",
        "Employment Contract",
        "Terms and Conditions",
        "Privacy Policy",
        "Data Protection Agreement",
        "Legal Notice",
        "Compliance Agreement",
        "Memorandum of Understanding",
        "Licensing Agreement",
        "Intellectual Property Policy",
        "Contract Renewal",
        "Regulatory Filing",
        "Legal Risk Assessment"
    ],

    "Security": [
        "Password Policy",
        "Incident Response Plan",
        "Vulnerability Assessment",
        "Firewall Configuration",
        "Encryption Standards",
        "Security Audit",
        "Access Control Policy",
        "Cybersecurity Awareness",
        "Threat Intelligence",
        "Multi Factor Authentication",
        "SIEM Monitoring",
        "Zero Trust Architecture",
        "Identity Management",
        "Patch Management",
        "Security Operations Report"
    ],

    "Operations": [
        "Daily Operations Report",
        "Inventory Management",
        "Logistics Planning",
        "Supply Chain Review",
        "Warehouse Operations",
        "Production Schedule",
        "Quality Assurance",
        "Vendor Coordination",
        "Business Continuity Plan",
        "Facility Maintenance",
        "Operational Risk Report",
        "Dispatch Schedule",
        "Asset Tracking",
        "Operational Metrics",
        "Resource Allocation"
    ],

    "Engineering": [
        "Software Design Document",
        "API Specification",
        "CI CD Pipeline",
        "Deployment Guide",
        "Code Review Checklist",
        "System Architecture",
        "Technical Documentation",
        "Microservices Design",
        "Cloud Infrastructure",
        "Database Schema",
        "Performance Optimization",
        "Testing Strategy",
        "DevOps Guidelines",
        "Application Monitoring",
        "Version Control Policy"
    ]
}

SENTENCES = [
    "This document has been reviewed by the department manager.",
    "Approval is required before implementation.",
    "All employees must comply with this policy.",
    "Internal use only.",
    "Version 2.1 of the document is currently active.",
    "Confidential information must not be shared externally.",
    "The policy shall be reviewed every year.",
    "Proper documentation must be maintained.",
    "Management approval is mandatory.",
    "This report contains organization specific information."
]

random.seed(42)

os.makedirs(DATASET_DIR, exist_ok=True)

ground_truth = []

for department, docs in DEPARTMENTS.items():

    folder = os.path.join(DATASET_DIR, department)
    os.makedirs(folder, exist_ok=True)

    for i, title in enumerate(docs, start=1):

        filename = f"{department.lower()}_{i}.txt"
        filepath = os.path.join(folder, filename)

        text = f"{title}\n\n"

        text += f"This document belongs to the {department} department.\n\n"

        for _ in range(10):
            text += random.choice(SENTENCES) + "\n"

        with open(filepath, "w", encoding="utf-8") as f:
            f.write(text)

        relative_path = filepath.replace("\\", "/")

        ground_truth.append([relative_path, department])

csv_path = os.path.join(BASE_DIR, "ground_truth.csv")

with open(csv_path, "w", newline="", encoding="utf-8") as f:

    writer = csv.writer(f)

    writer.writerow(["filepath", "department"])

    writer.writerows(ground_truth)

print("=" * 50)
print("Dataset Generated Successfully")
print(f"Documents : {len(ground_truth)}")
print(f"CSV Saved : {csv_path}")
print("=" * 50)