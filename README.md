# Advanced Data Visualization (MIACD) 2025/26 - Final Project

This project was developed for the Advanced Data Visualization course (MIACD) 2025/26 at the University of Coimbra. It consists of an interactive visualization application built with Plotly/Dash in Python, designed to support exploratory analysis and visual communication of healthcare data from the Portuguese Transparency Portal (Portal da Transparência).

The dashboard provides multiple coordinated views and interactive filtering mechanisms to analyze activity, financial evolution, institutional stress, medicines, and SNS accounts across Portuguese healthcare institutions.

---

## Team

This project was developed by a group of 2 students:

- **Cláudio Catarino** — uc2022224320@student.uc.pt
- **Samuel Crespo** — uc2025178373@student.uc.pt

---

## Project Goals

The main objective of this project is to provide an interactive dashboard capable of answering analytical questions regarding the Portuguese National Health System (SNS).

The application includes:

- Multiple coordinated visualization views
- Advanced interaction techniques
- Temporal filtering and regional drill-down
- Geospatial visualizations
- Comparative financial and operational analysis
- Accessibility-oriented visual design choices

---

## Repository Structure

The project follows a modular architecture that separates preprocessing, visualization pages, helper functions, and datasets.

```text
VAD2026/
│
├── data/
│   ├── raw/                    # Original datasets from Portal da Transparência
│   └── processed/              # Cleaned and processed datasets used by the dashboard
│
├── notebooks/                  # Exploratory Data Analysis notebooks
│
├── src/
│   ├── assets/
│   │   └── style.css           # Dashboard styling
│   │
│   ├── map/                    # Geospatial shapefiles and map resources
│   │
│   ├── pages/                  # Dashboard pages
│   │   ├── dashboard.py
│   │   ├── mapa.py
│   │   ├── stress.py
│   │   ├── financeira.py
│   │   ├── medicamentos.py
│   │   ├── contas.py
│   │   └── pages_helper.py
│   │
│   ├── app.py                  # Main Dash application and router
│   ├── create_master_df.py     # Creates integrated master dataset
│   ├── download_raw_data.py    # Downloads raw datasets
│   ├── process_raw_data.py     # Cleans and preprocesses raw data
│   └── utils.py                # Shared helper functions
│
├── requirements.txt
└── README.md
```

---

## Main Dashboard Pages

The dashboard includes the following analytical pages:

- **Dashboard Geral** — General overview of healthcare activity
- **Mapa Regional** — Regional and institutional geospatial analysis
- **Stress Hospitalar** — Stress indicators based on healthcare demand and staff capacity
- **Evolução Financeira** — Financial evolution and execution analysis
- **Medicamentos** — Analysis of SNS expenditure on medicines
- **Contas SNS** — Budget and financial execution analysis

---

## Prerequisites

Before running the project, ensure the following are installed:

- Python 3.9+
- `pip`

---

## Setup and Execution

### 1. Clone the repository

```bash
git clone https://github.com/claudio3472/VAD2026.git
cd VAD2026
```

### 2. Create and activate a virtual environment

```bash
python -m venv venv
```

#### Windows

```bash
venv\Scripts\activate
```

#### Mac/Linux

```bash
source venv/bin/activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

---

## Data Preparation

To load, clean, and standardize the data from the Transparency Portal, run:

```bash
python src/download_raw_data.py
python src/process_raw_data.py
python src/create_master_df.py
```

The processed datasets will be stored in:

```text
data/processed/
```

---

## Running the Dashboard

After preprocessing the data, launch the dashboard with:

```bash
python src/app.py
```

The application will be available at:

```text
http://127.0.0.1:8050
```

---

## Technologies Used

- Python
- Dash
- Plotly
- Pandas
- NumPy
- GeoPandas
- Shapely

---

## Data Source

The datasets used in this project were obtained from:

- Portal da Transparência — SNS Portugal
