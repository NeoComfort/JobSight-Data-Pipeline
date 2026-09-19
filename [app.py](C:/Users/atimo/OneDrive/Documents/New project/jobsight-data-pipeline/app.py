"""Web dashboard for the JobSight data pipeline."""

from __future__ import annotations

import sqlite3
from collections import Counter

from flask import Flask, render_template

from pipeline import DATABASE_PATH, run_pipeline

app = Flask(__name__)


def get_dashboard_data() -> dict:
    """Load the latest pipeline output into dashboard-friendly values."""
    run_pipeline()
    with sqlite3.connect(DATABASE_PATH) as connection:
        total_jobs = connection.execute("SELECT COUNT(*) FROM job_listings").fetchone()[0]
        locations = connection.execute(
            "SELECT province, COUNT(*) FROM job_listings GROUP BY province ORDER BY COUNT(*) DESC, province"
        ).fetchall()
        employment_types = connection.execute(
            "SELECT employment_type, COUNT(*) FROM job_listings GROUP BY employment_type ORDER BY COUNT(*) DESC"
        ).fetchall()
        recent_jobs = connection.execute(
            """
            SELECT title, company, location, province, employment_type, posted_date
            FROM job_listings ORDER BY posted_date DESC LIMIT 5
            """
        ).fetchall()
        salary_midpoint = connection.execute(
            """
            SELECT ROUND(AVG((salary_min + salary_max) / 2.0), 2)
            FROM job_listings WHERE salary_min IS NOT NULL AND salary_max IS NOT NULL
            """
        ).fetchone()[0]
        skill_rows = connection.execute("SELECT skills FROM job_listings").fetchall()

    skills = Counter(
        skill.strip() for (skill_list,) in skill_rows for skill in skill_list.split(",") if skill.strip()
    )
    return {
        "total_jobs": total_jobs,
        "salary_midpoint": f"R {salary_midpoint:,.0f}" if salary_midpoint else "No data",
        "locations": locations,
        "employment_types": employment_types,
        "top_skills": skills.most_common(5),
        "recent_jobs": recent_jobs,
    }


@app.get("/")
def dashboard():
    return render_template("index.html", **get_dashboard_data())


if __name__ == "__main__":
    app.run(debug=True)
