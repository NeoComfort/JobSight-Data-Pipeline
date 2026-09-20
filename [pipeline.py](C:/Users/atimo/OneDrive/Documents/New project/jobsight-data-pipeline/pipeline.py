"""ETL pipeline for the JobSight portfolio project."""

from __future__ import annotations

import csv
import sqlite3
from collections import Counter
from dataclasses import dataclass
from datetime import date
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent
RAW_DATA_PATH = PROJECT_ROOT / "data" / "raw" / "jobs.csv"
OUTPUT_DIR = PROJECT_ROOT / "data" / "output"
DATABASE_PATH = OUTPUT_DIR / "jobsight.db"
REJECTED_ROWS_PATH = OUTPUT_DIR / "rejected_rows.csv"
REPORT_PATH = OUTPUT_DIR / "analytics-report.md"

REQUIRED_COLUMNS = {
    "job_id", "title", "company", "location", "province",
    "employment_type", "posted_date", "skills",
}


@dataclass(frozen=True)
class Job:
    job_id: str
    title: str
    company: str
    location: str
    province: str
    employment_type: str
    posted_date: str
    salary_min: int | None
    salary_max: int | None
    skills: str


def normalise_text(value: str | None) -> str:
    """Trim a string and turn repeated spaces into one space."""
    return " ".join((value or "").strip().split())


def parse_salary(value: str | None, field_name: str) -> int | None:
    value = normalise_text(value).replace(" ", "").replace(",", "")
    if not value:
        return None
    if not value.isdigit():
        raise ValueError(f"{field_name} must be a whole number")
    return int(value)


def transform_row(row: dict[str, str], seen_ids: set[str]) -> Job:
    missing = [column for column in REQUIRED_COLUMNS if not normalise_text(row.get(column))]
    if missing:
        raise ValueError(f"missing required value(s): {', '.join(sorted(missing))}")

    job_id = normalise_text(row["job_id"])
    if job_id in seen_ids:
        raise ValueError("duplicate job_id")

    posted_date = normalise_text(row["posted_date"])
    try:
        date.fromisoformat(posted_date)
    except ValueError as error:
        raise ValueError("posted_date must use YYYY-MM-DD") from error

    salary_min = parse_salary(row.get("salary_min"), "salary_min")
    salary_max = parse_salary(row.get("salary_max"), "salary_max")
    if salary_min is not None and salary_max is not None and salary_max < salary_min:
        raise ValueError("salary_max cannot be below salary_min")

    seen_ids.add(job_id)
    return Job(
        job_id=job_id,
        title=normalise_text(row["title"]).title(),
        company=normalise_text(row["company"]),
        location=normalise_text(row["location"]).title(),
        province=normalise_text(row["province"]).title(),
        employment_type=normalise_text(row["employment_type"]).title(),
        posted_date=posted_date,
        salary_min=salary_min,
        salary_max=salary_max,
        skills=normalise_text(row["skills"]).lower(),
    )


def extract_and_transform(input_path: Path) -> tuple[list[Job], list[dict[str, str]]]:
    """Read CSV input and split clean rows from rejected rows."""
    accepted: list[Job] = []
    rejected: list[dict[str, str]] = []
    seen_ids: set[str] = set()

    with input_path.open(newline="", encoding="utf-8") as source:
        reader = csv.DictReader(source)
        source_columns = set(reader.fieldnames or [])
        missing_columns = REQUIRED_COLUMNS - source_columns
        if missing_columns:
            raise ValueError(f"Input CSV missing columns: {', '.join(sorted(missing_columns))}")

        for row in reader:
            try:
                accepted.append(transform_row(row, seen_ids))
            except ValueError as error:
                rejected.append({**row, "rejection_reason": str(error)})

    return accepted, rejected


def initialise_database(connection: sqlite3.Connection) -> None:
    connection.executescript(
        """
        DROP TABLE IF EXISTS job_listings;
        CREATE TABLE job_listings (
            job_id TEXT PRIMARY KEY,
            title TEXT NOT NULL,
            company TEXT NOT NULL,
            location TEXT NOT NULL,
            province TEXT NOT NULL,
            employment_type TEXT NOT NULL,
            posted_date TEXT NOT NULL,
            salary_min INTEGER,
            salary_max INTEGER,
            skills TEXT NOT NULL
        );
        """
    )


def load_jobs(connection: sqlite3.Connection, jobs: list[Job]) -> None:
    connection.executemany(
        """
        INSERT INTO job_listings VALUES
        (:job_id, :title, :company, :location, :province, :employment_type,
         :posted_date, :salary_min, :salary_max, :skills)
        """,
        [job.__dict__ for job in jobs],
    )
    connection.commit()


def write_rejected_rows(rejected: list[dict[str, str]]) -> None:
    fieldnames = [
        "job_id", "title", "company", "location", "province", "employment_type",
        "posted_date", "salary_min", "salary_max", "skills", "rejection_reason",
    ]
    with REJECTED_ROWS_PATH.open("w", newline="", encoding="utf-8") as destination:
        writer = csv.DictWriter(destination, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rejected)


def query_rows(connection: sqlite3.Connection, query: str) -> list[tuple]:
    return connection.execute(query).fetchall()


def markdown_table(headers: list[str], rows: list[tuple]) -> str:
    output = [f"| {' | '.join(headers)} |", f"| {' | '.join(['---'] * len(headers))} |"]
    output.extend(f"| {' | '.join(str(value) for value in row)} |" for row in rows)
    return "\n".join(output)


def write_report(connection: sqlite3.Connection, accepted_count: int, rejected_count: int) -> None:
    locations = query_rows(
        connection,
        "SELECT province, COUNT(*) AS listings FROM job_listings GROUP BY province ORDER BY listings DESC, province",
    )
    employment_types = query_rows(
        connection,
        "SELECT employment_type, COUNT(*) AS listings FROM job_listings GROUP BY employment_type ORDER BY listings DESC",
    )
    salaries = query_rows(
        connection,
        "SELECT ROUND(AVG((salary_min + salary_max) / 2.0), 2) FROM job_listings WHERE salary_min IS NOT NULL AND salary_max IS NOT NULL",
    )
    skills = Counter(
        skill.strip()
        for (skill_list,) in query_rows(connection, "SELECT skills FROM job_listings")
        for skill in skill_list.split(",")
        if skill.strip()
    )
    top_skills = [(skill, count) for skill, count in skills.most_common(5)]
    average_salary = salaries[0][0] if salaries and salaries[0][0] is not None else "No salary data"

    report = f"""# JobSight Analytics Report

Generated by `pipeline.py`.

- Accepted records: **{accepted_count}**
- Rejected records: **{rejected_count}**
- Average listed salary midpoint: **{average_salary}**

## Listings by province

{markdown_table(['Province', 'Listings'], locations)}

## Listings by employment type

{markdown_table(['Employment type', 'Listings'], employment_types)}

## Most requested skills

{markdown_table(['Skill', 'Mentions'], top_skills)}
"""
    REPORT_PATH.write_text(report, encoding="utf-8")


def run_pipeline(input_path: Path = RAW_DATA_PATH) -> tuple[int, int]:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    jobs, rejected = extract_and_transform(input_path)
    write_rejected_rows(rejected)
    with sqlite3.connect(DATABASE_PATH) as connection:
        initialise_database(connection)
        load_jobs(connection, jobs)
        write_report(connection, len(jobs), len(rejected))
    return len(jobs), len(rejected)


if __name__ == "__main__":
    accepted, rejected = run_pipeline()
    print(f"Pipeline complete: {accepted} accepted, {rejected} rejected.")
    print(f"Database: {DATABASE_PATH}")
    print(f"Report: {REPORT_PATH}")
