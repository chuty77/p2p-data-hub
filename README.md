# P2P Data Hub — ERP Master Data Governance & Three-Way Match

**Python · REST/OData API · SQL Server · Power BI**

An end-to-end data pipeline that prepares Procure-to-Pay data for an ERP migration, modeled on Microsoft Dynamics 365 Finance & Operations. It integrates data from two systems, enforces vendor master data quality before migration, produces a D365-style import file, and gives Finance a three-way match control dashboard.

> **Note:** all data is synthetic. A generator script creates vendors, items, purchase orders, receipts and invoices, with data quality problems injected on purpose so the pipeline has real issues to catch. All company names are fictional.

![Master Data Readiness](images/01_master_data_readiness.png)

---

## The business problem

A company is maturing its ERP and needs to move vendor and purchasing data into it. The data lives in two places:

- A **legacy ERP** that exports vendor and item master data as CSV files, full of duplicates, missing tax IDs and non-standard values.
- A **procurement platform** that exposes purchase orders, product receipts and vendor invoices through a paginated REST API in OData format, the same format D365 uses.

Finance needs to answer three questions:

1. **Which vendors are safe to migrate** into the new ERP, and which need a data owner's review first?
2. **Which invoices should not be paid automatically**, because they don't match what was ordered and received?
3. **Where is the money going**, with one trusted source instead of spreadsheets?

---

## Architecture

```
 Legacy ERP (CSV) ──────┐
                        ├──► EXTRACT (Python) ──► VALIDATE & TRANSFORM (Python) ──► LOAD (Python)
 Procurement API ───────┘    · OData pagination     · 6 data quality rules             · SQL Server
 (REST, JSON pages)          · HTTP error checks    · auto-fix approved values          · audit columns
                             · row-count logs       · dedupe → golden record + xref
                                                    · D365 import file + exceptions
                                                                   │
                                                                   ▼
                                                    SQL SERVER — STAR SCHEMA
                                                    dim_vendor · dim_item · dim_date
                                                    fact_po_line · fact_receipt · fact_invoice
                                                    fact_three_way_match
                                                                   │
                                                                   ▼
                                                    POWER BI — 3 report pages
```

---

## What the pipeline does

### 1. Extract
- Reads every page of each API entity by following `@odata.nextLink` until the last page.
- Stops on HTTP errors (`raise_for_status`) so incomplete data never loads silently.
- Reads legacy CSVs as text, keeping values exactly as they came from the source.
- Logs row counts at every step to reconcile against the source.

### 2. Validate & transform (vendor master data)

| Rule | Description | Severity | Action | Blocks migration |
|---|---|---|---|---|
| VEN-001 | Missing Tax ID | High | Flag | Yes |
| VEN-002 | Invalid currency code | High | Flag | Yes |
| VEN-003 | Missing or invalid AP email | Low | Flag | No |
| VEN-004 | Non-standard payment terms | Low / Medium | Auto-fix if the value is in the Finance-approved mapping; otherwise flag | Only if not fixable |
| VEN-005 | Duplicate vendor (same Tax ID) | High | Merge into the oldest record | No (resolved) |
| VEN-006 | Possible duplicate (same name, different Tax ID) | Medium | Flag for human review, never auto-merge | Yes |

Design principles:
- **Only fix what Finance has approved.** Mappings like `N30 → Net30` are corrected automatically; a term like `2% 10 Net 30` is not, because converting it would silently drop an early-payment discount.
- **Every change is logged** with the rule, the record, the original value and what was done.
- **Raw staging data is never modified.** All transformations run on copies.
- **Tax ID identifies the legal entity**, so Tax ID matches are merged; name-only matches are sent to review, because merging two different companies could send payments to the wrong vendor.

Outputs:
- **Golden record:** one row per real vendor, with a new D365-style account number (`VEND-00001`).
- **Cross-reference (xref):** every legacy code mapped to its new account, so historical transactions still point to the right vendor.
- **`Vendors_V2_import.csv`:** only migration-ready vendors, with D365 data entity field names.
- **`blocking_issues_for_review.csv`:** the work list for data owners.

### 3. Load & model (SQL Server)
- Staging and governed tables are loaded with audit columns (`_LoadedAt`, `_SourceSystem`).
- A star schema is built with SQL scripts. Orphan transactions point to an **Unknown member** instead of being dropped, so totals reconcile with the source and data gaps stay visible.

### 4. Three-way match (SQL)
Each invoice line gets exactly one status, in priority order:

| Priority | Status | Rule |
|---|---|---|
| 1 | Duplicate invoice | Same vendor, invoice number and PO line submitted more than once |
| 2 | Unknown vendor | The vendor does not exist in the master |
| 3 | No receipt | Invoiced before any goods were received |
| 4 | Qty variance | Cumulative invoiced quantity exceeds received quantity |
| 5 | Price variance | Invoice price differs from the PO price by more than 5% |
| 6 | Matched | Everything agrees; safe to pay |

Built with CTEs and window functions: `ROW_NUMBER() OVER (PARTITION BY ...)` to detect duplicates, and a running `SUM() OVER (...)` to catch vendors that split one PO line across several invoices.

---

## Results

| Metric | Value |
|---|---|
| Legacy vendors → golden records | 43 → 41 |
| Vendors ready to load into D365 | 36 (87.8%) |
| Vendors routed to data owners | 5 |
| PO lines saved from being orphaned by the xref | 22 (≈6% of all lines) |
| Invoice lines matched | 73.5% |
| Invoiced amount on hold for review | $1.10M |

### Key findings

- **Merging duplicates changed the vendor ranking.** After the Tax ID merge, AeroTech Fasteners became the top vendor by spend. Without the cross-reference, its spend would have been split across two codes.
- **Two of the five blocked vendors are in the top 10 by spend.** Combining the data quality view with the spend view tells the business which fixes to prioritize first, because a vendor that can't be migrated can't be paid in the new system.
- **Missing receipts are almost as large as price variances.** That points to a process gap in receiving, not only a vendor pricing issue.
- **An invoice can have more than one problem.** Each line shows its highest-priority status, while conditional formatting still flags secondary issues such as a price difference on an invoice with no receipt.

---

## Dashboard

### Master Data Readiness
*Which vendors are ready to migrate to D365?* Readiness KPIs, data quality issues by rule and severity, and the list of blocking issues to resolve.

![Master Data Readiness](images/01_master_data_readiness.png)

### Three-Way Match Control
*Which invoices should not be paid automatically?* Match rate, amount on hold, price variance and duplicate exposure, with the list of invoices on hold for Accounts Payable.

![Three-Way Match Control](images/02_three_way_match.png)

### Spend Analysis
*Where is the money going?* Monthly spend, top vendors, and spend by category and site.

![Spend Analysis](images/03_spend_analysis.png)

---

## Project structure

```
p2p-data-hub/
├── config.py                     paths, API and database settings, business rules
├── src/
│   ├── generate_source_data.py   simulated source systems with injected data problems
│   ├── extract.py                OData API client with pagination + CSV reader
│   ├── validate_transform.py     data quality rules, dedupe, golden record, xref, D365 files
│   └── load.py                   loads staging and governed tables into SQL Server
├── sql/
│   ├── 00_exploration.sql        reconciliation and orphan checks
│   ├── 01_dimensions.sql         dim_vendor, dim_item, dim_date
│   └── 02_facts.sql              fact tables and three-way match
├── powerbi/P2P_Data_Hub.pbix
├── output/                       D365 import file and exceptions (generated)
└── images/                       dashboard screenshots
```

---

## How to run it

**Requirements:** Python 3.10+, SQL Server (Express works), ODBC Driver 17 or 18 for SQL Server, Power BI Desktop.

```bash
pip install pandas requests sqlalchemy pyodbc
```

1. **Generate the source data**
   ```bash
   python src/generate_source_data.py
   ```
2. **Start the mock API** in a second terminal
   ```bash
   cd mock_api
   python -m http.server 8000
   ```
3. **Create the database** in SQL Server: `CREATE DATABASE P2PDataHub;` and set `SQL_SERVER` and `ODBC_DRIVER` in `config.py`.
4. **Run the pipeline**
   ```bash
   python src/load.py
   ```
5. **Build the model:** run `sql/01_dimensions.sql` and then `sql/02_facts.sql` against `P2PDataHub`.
6. **Open** `powerbi/P2P_Data_Hub.pbix` and refresh.

---

## Moving to production

| This project | Production equivalent |
|---|---|
| Mock API on `localhost` | D365 OData endpoint, authenticated with a Microsoft Entra ID token (MSAL) |
| CSV vendor import file | D365 Data Management Framework data package |
| Full reload on every run | Incremental loads filtered by modified date |
| Manual run | Scheduled with Azure Data Factory or Airflow |
| Business rules in `config.py` | Rules owned by Finance in a governed configuration table |
| SQL Server Express | SQL Server, Azure SQL or Microsoft Fabric |

---

## Author

**Paulo Quirós Guerrero** — Data Analyst | Data Quality & Analytics Engineering
[LinkedIn](https://www.linkedin.com/in/paulo-e-quiros-guerrero-bb1b5418a) · [Portfolio](https://github.com/chuty77/data-analytics-portfolio)
