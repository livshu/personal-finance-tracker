# Personal Finance Tracker

A Django based personal finance tracker project built as a personal requirement (mainly after the frustration of not being able to split joint expenses on a tracker) and a learning tool!

## Project goal
- track personal and joint finances 
- support manual CSV based transaction imports
- provide useful analytics and dashboard views
- build more full stack and data modelling skills using Django 


## Current scope

Current version includes:

- a Django project with one app: `core`
- initial finance data models:
  - `Account`
  - `Category`
  - `Transaction`
- Django admin configuration for managing records
- initial model tests
- documentation for roadmap, architecture, and data model decisions

## Tech stack

- Python
- Django
- SQLite 

## Data model overview

The initial data model is centred on `Transaction`, supported by:

- `Account` for where money is held or spent from
- `Category` for classifying income and spending transactions

This structure is intended to support future work such as:
- CSV imports
- transaction categorisation
- monthly summaries
- dashboard views
- personal vs joint spending analysis

## Running the project locally

1. Create and activate a virtual environment
2. Install dependencies
3. Run migrations
4. Start the development server

Example commands:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python manage.py migrate
python manage.py runserver

Then open:

http://127.0.0.1:8000/

Admin is available at:

http://127.0.0.1:8000/admin/