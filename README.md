# Pediatric Growth Tracking Application

A full-stack Flask web application for entering, storing, editing, and visualizing child growth measurements over time.

The application allows users to add growth records through a web form, persist measurements in a SQLite database, view historical entries in a table, update or delete records, and generate growth charts directly in the browser.

## Features

- Add child growth measurements through a web form
- Store historical measurements in SQLite
- View all records in a data table
- Edit existing measurements
- Delete records
- Generate dynamic growth charts
- Run locally as a Flask application

## Tech Stack

- Python
- Flask
- SQLite
- HTML
- CSS
- JavaScript
- Matplotlib / data visualization

## Project Structure

```text
kids-growth-charts/

web/
    app.py
    database.py
    migrate.py
    demo_growth_charts.db
    static/
    templates/

README.md
requirements.txt
```

## How to Run Locally

Create and activate a virtual environment:

```bash
python -m venv .venv
source .venv/bin/activate
```

Install dependencies:

```bash
pip install -r requirements.txt
```

Move into the web app directory:

```bash
cd web
```

Run the Flask app:

```bash
python app.py
```

Open the app in your browser:

```text
http://127.0.0.1:5000
```

## Skills Demonstrated

- Full-stack Flask application development
- Database-backed CRUD functionality
- SQLite database design
- Form handling and user input validation
- Dynamic chart generation
- Data table rendering
- Frontend/backend integration
- Practical data visualization

## Deployment

The Flask web application is configured for deployment with Render.

Production build command:

```bash
pip install -r requirements-web.txt
```

Production start command:

```bash
gunicorn web.app:app
```

The deployed demo uses a non-private sample SQLite database generated from `data/dummy_data.json`. Personal family data is excluded from version control.

## Future Improvements

- Deploy the Flask app publicly
- Add user authentication
- Support multiple children or profiles
- Add percentile reference curves
- Improve mobile responsiveness
- Add export options for historical data

## Motivation

This project was built to practice full-stack Python web development while creating a practical data management and visualization tool. It demonstrates how user-entered data can be stored, managed, and visualized through a database-backed web application.
