
---

## 📁 .streamlit/
> Streamlit configuration files

- `config.toml`: Page title, layout, theming, etc.
- Used automatically when you deploy (e.g. Streamlit Cloud)

---

## 📁 archive/
> Legacy, experimental, or deprecated code

- Old ETL versions, page prototypes, etc.
- Not used in production but kept for reference

---

## 📁 auth/
> Authentication and user session logic

- `authenticator.py`: Login, signup, password hashing
- Connects to `users` table in your OLTP DB
- Uses `streamlit-authenticator`

---

## 📁 data/
> Static data files (external inputs)

- Raw `.csv` files used for:
  - Initial DB population
  - Routines
  - Muscle mapping
- Often loaded once via ETL scripts

---

## 📁 database/
> All data connection logic (OLTP + external)

- `db_connector.py`: SQLAlchemy connection to MySQL
- `gsheet_connector.py`: Reads from Google Sheets (if used)
- `data_validation.py`: Optional checks on raw inputs

---

## 📁 pages/
> Streamlit sidebar pages

Each file here becomes a page in the sidebar navigation.

Examples:
- `analytics1_overview.py`: App-level summary
- `analytics2_progress.py`: Time-based KPIs
- `routinetemplates.py`: Manage user-defined routines

---

## 📁 services/
> Core logic: ETLs, transformations, feature engineering

- `etl_oltp_to_olap.py`: Transforms logs → OLAP tables
- `etl_olap_to_oltp.py`: (if needed)
- `feature_eng.py`: Derive volume, intensity, RIR, etc.
- `datawrangling.py`: App-specific data cleaning

💡 If the logic is project-specific, it belongs here.

---

## 📁 utils/
> General-purpose, reusable helper functions

- `charts.py`: Custom plots for Streamlit
- `kpis.py`: Metrics calculation
- `styling.py`: CSS-like tweaks and formatting
- `tables.py`: Pretty table rendering
- `data_loader.py`: DB reads with caching

💡 If it’s generic, stateless, and reusable — it goes here.

---

## 📁 tests/ (optional)
> Unit or integration tests

- `test_etl.py`, `test_auth.py`, etc.
- Recommended to use with `pytest`

---

## 🧠 Data Architecture Summary

| Layer       | Description                                |
|-------------|--------------------------------------------|
| **OLTP**    | Raw user inputs (workouts, sets, users)    |
| **OLAP**    | Aggregated metrics (fact/dim schema)       |
| **ETL**     | Python pipelines from OLTP → OLAP (`/services`) |
| **Frontend**| Streamlit app using data from both layers  |

---

## 🛠 Deployment Options

- Run locally with `streamlit run app.py`
- Deploy to Streamlit Cloud for team access
- Use Docker or a VM for more advanced hosting

---

Feel free to adjust this structure as your app grows! 🚀