# Installation & User Configuration Guide

This guide explains how to install dependencies, initialize testing datasets, and deploy the StackCheck DP Data Validation Platform offline.

---

## System Requirements

- **Python**: 3.12 or higher
- **Node.js**: 20 or higher
- **Docker**: Optional (for web browser environment)

---

## Step 1: Install Python Backend

1. Navigate to the `backend/` directory:
   ```bash
   cd backend
   ```
2. Create and activate a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```
3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

---

## Step 2: Initialize Mock Dataset & Spec Files

We have provided a mock dataset generator script to create SPSS SAV files containing common DP formatting issues for testing.

Run the generator:
```bash
python app/samples/generate_mock_data.py
```
This generates:
- [sample_spec.csv](file:///Users/chethan/Desktop/StackCheck/backend/app/samples/sample_spec.csv) (DP Reference Spec)
- `sample_dataset.csv` (CSV Dataset)
- `sample_dataset.sav` (SPSS Dataset)

---

## Step 3: Install Frontend

1. Navigate to the `frontend/` directory:
   ```bash
   cd ../frontend
   ```
2. Install npm packages:
   ```bash
   npm install
   ```
3. Run development server:
   ```bash
   npm run dev
   ```

---

## Step 4: Run via Docker (Alternative Web Setup)

If you prefer to deploy StackCheck in a web-accessible browser environment (e.g. for multiple local users), use Docker:

```bash
docker-compose up --build
```
- **Backend API**: `http://localhost:8000`
- **Frontend Dashboard**: `http://localhost:80`

---

## Step 5: SPSS Reference Specification Template format

The validation engine matches variables against a structured Reference Sheet template:

| Column Name | Type | Description |
| :--- | :--- | :--- |
| `variable_name` | Text | Name in dataset (`RESP_ID`, `BRAND`, `AGE`) |
| `variable_label` | Text | Desired SPSS metadata label description |
| `category` | Text | Classification: `Core`, `Brand`, `Dependent`, `CEP`, `Imagery`, `Strategic` |
| `required` | Boolean | `Yes`/`No` (whether presence is mandatory) |
| `data_type` | Text | Expected format: `Integer`, `Float`, `String`, `Boolean`, `Date` |
| `is_binary` | Boolean | `Yes`/`No` (forces strict 0/1 checking for yes/no conditions) |
| `expected_values` | Text | Semicolon-separated allowed codes (e.g., `1;2;3`) |
| `value_labels` | Text | Semicolon-separated value labels mappings (e.g. `1=Male; 2=Female`) |
