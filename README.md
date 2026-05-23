# Personal Finance Tracker

A full-stack personal finance management application designed to help users track income and expenses, automatically categorize transactions using machine learning, and visualize financial patterns through interactive dashboards.

The project combines traditional rule-based categorization with a Scikit-learn machine learning pipeline to provide semi-automated financial organization and analytics capabilities.

This repository was developed using a heavily AI-assisted software development workflow for rapid prototyping, feature integration, debugging, and architecture iteration. 

---

# Project Overview

The application provides a lightweight finance tracking system with:

* Expense and income management
* ML-assisted transaction categorization
* Interactive financial visualizations
* SQLite-based persistence
* Customizable category taxonomies
* Hybrid rule-based + machine learning workflows

The project explores practical applications of machine learning in personal finance management while maintaining a beginner-friendly architecture and local deployment workflow.

---

# AI-Assisted Development Workflow

This project was developed using a strongly AI-assisted engineering workflow where generative AI tools were extensively utilized during development.

AI-assisted workflows contributed to:

* Streamlit UI scaffolding
* Backend logic generation
* SQLite integration workflows
* Machine learning pipeline setup
* Visualization generation
* Debugging and troubleshooting
* Application architecture iteration
* Documentation refinement
* Rapid prototyping and experimentation

The project demonstrates how modern AI-assisted development methodologies can accelerate full-stack application development and ML integration workflows. 

---

# Core Features

* Add income and expense transactions
* ML-based transaction categorization
* Rule-based fallback categorization
* Editable category taxonomy using CSV
* SQLite database persistence
* Transaction deletion support
* Interactive financial dashboards
* Cashflow and spending trend analysis
* Category-wise analytics
* Rolling average financial analysis
* Date-range and category filtering

---

# Technology Stack

## Frontend & UI

| Technology | Purpose                        |
| ---------- | ------------------------------ |
| Streamlit  | Interactive web application UI |
| Plotly     | Financial data visualization   |

---

## Backend & Data

| Technology | Purpose                        |
| ---------- | ------------------------------ |
| SQLite     | Local database storage         |
| Pandas     | Data manipulation and analysis |

---

## Machine Learning

| Technology          | Purpose                        |
| ------------------- | ------------------------------ |
| Scikit-learn        | ML pipeline and classification |
| TF-IDF Vectorizer   | Text feature extraction        |
| Logistic Regression | Transaction classification     |

---

## Language & Runtime

| Technology   | Purpose                   |
| ------------ | ------------------------- |
| Python 3.10+ | Core programming language |

---

# Repository Structure

```plaintext id="9f0m2z"
Personal_Finance_Tracker/
├─ app/
│  ├─ main.py
│  ├─ analysis.py
│  ├─ budget.py
│  ├─ categorizer.py
│  ├─ db_handler.py
│  └─ train_model.py
│
├─ data/
│  ├─ categories.csv
│  └─ transactions.db
│
├─ models/
│  └─ model.pkl
│
├─ requirements.txt
├─ runtime.txt
└─ README.md
```

---

# Machine Learning Workflow

The categorization system uses a hybrid approach:

1. Transaction descriptions are vectorized using TF-IDF
2. A Logistic Regression classifier predicts the category
3. Confidence thresholds are evaluated
4. Low-confidence predictions fallback to keyword-based rules
5. Unmatched entries default to `Other`

This approach combines flexibility, interpretability, and robustness for beginner-level financial NLP experimentation.

---

# Visualization Features

The dashboard system includes:

* Monthly spending analysis
* Category-wise spending breakdown
* Cashflow trends
* Cumulative savings tracking
* Spending heatmaps
* Rolling average expenditure analysis
* Category trend analysis over time

Interactive filtering allows users to analyze spending patterns dynamically across date ranges and categories.

---

# Key Engineering Challenges Explored

* Combining ML predictions with rule-based systems
* SQLite schema evolution and migration handling
* Real-time dashboard rendering with Streamlit
* Dynamic category management workflows
* Model persistence and retraining
* Maintaining scikit-learn version consistency
* Interactive state management in Streamlit

---

# Educational Purpose

This repository is intended for:

* Machine learning experimentation
* Full-stack Python application learning
* Streamlit dashboard development
* Financial analytics exploration
* Practical Scikit-learn workflows
* Beginner ML deployment understanding

---

# Future Improvements

Planned future enhancements include:

* Budget tracking and alerts
* Smart financial recommendations
* CSV and bank statement import support
* Multi-user authentication
* Cloud database integration
* Real-time analytics
* Expense forecasting models
* Personalized financial insights
* Mobile-responsive redesign

---

# Quick Start

Clone the repository:

```bash id="h8u9x2"
git clone https://github.com/shashe9/Personal_Finance_Tracker.git
```

Install dependencies:

```bash id="0e5s7k"
pip install -r requirements.txt
```

Train the ML model:

```bash id="y3f2mw"
python app/train_model.py
```

Run the application:

```bash id="l4z6qn"
streamlit run app/main.py
```

---

# Important Note

This repository reflects a learning-oriented and experimentation-focused finance analytics project developed with significant AI-assisted software engineering workflows. The project is educational in nature and intended for portfolio, experimentation, and learning purposes rather than enterprise-grade financial deployment.

---

# Author

**Shashank Shekhar**
Computer Science Engineering Undergraduate
2026
