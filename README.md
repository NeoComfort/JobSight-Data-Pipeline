# JobSight Data Pipeline

JobSight is a beginner-friendly data engineering project that turns raw job-listing data into a clean SQLite database and an analytics report. It demonstrates an end-to-end ETL process:

1. **Extract** raw records from a CSV file.
2. **Transform** values into consistent, validated formats.
3. **Load** accepted records into SQLite and log rejected records.
4. **Analyse** the cleaned data with SQL and export a Markdown report.

## What this project demonstrates

- CSV ingestion and data-quality checks
- Cleaning text, dates, and salary fields
- Handling duplicate and invalid records
- Loading relational data with SQLite
- Writing and using SQL aggregation queries
- Producing a repeatable report from a pipeline

## Project structure

```text
jobsight-data-pipeline/
├── app.py                        # Flask dashboard server
├── pipeline.py                   # ETL pipeline
├── requirements.txt
├── templates/index.html           # Dashboard HTML
├── static/style.css               # Dashboard styling
├── data/raw/jobs.csv              # Input data
├── data/output/                   # Created when the pipeline runs
├── sql/analytics.sql              # Queries used in the report
├── tests/test_pipeline.py         # Automated checks
└── README.md
