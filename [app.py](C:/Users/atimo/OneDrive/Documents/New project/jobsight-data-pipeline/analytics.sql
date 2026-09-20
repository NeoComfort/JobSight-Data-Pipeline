-- Listings grouped by province
SELECT province, COUNT(*) AS listings
FROM job_listings
GROUP BY province
ORDER BY listings DESC, province;

-- Employment-type distribution
SELECT employment_type, COUNT(*) AS listings
FROM job_listings
GROUP BY employment_type
ORDER BY listings DESC;

-- Average midpoint where both salary values are available
SELECT ROUND(AVG((salary_min + salary_max) / 2.0), 2) AS average_salary_midpoint
FROM job_listings
WHERE salary_min IS NOT NULL AND salary_max IS NOT NULL;
