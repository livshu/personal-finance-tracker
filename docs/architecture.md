# Architecture

## Overview

This project is a Django based personal finance tracker intended for personal use and as a learning/portfolio project.

The first phase focuses on building strong foundations before adding more advanced analytics or dashboard features. The current architecture is simple for now:

- one Django project: `config`
- one Django app: `core`
- SQLite for local development
- Django admin for early data management and validation

## Current structure

### `config/`

The Django project configuration package. It contains the global project setup, including:

- `settings.py` for installed apps, database configuration, and general Django settings
- `urls.py` for top-level URL routing
- `asgi.py` and `wsgi.py` for deployment entry points

`config` is responsible for project level wiring

### `core/`

The main application for the finance domain.

It currently contains:

- models for `Account`, `Category`, and `Transaction`
- admin registration for those models
- initial automated tests

The `core` app is the centre of the first version of the project and is responsible for the main finance data structures.

### `manage.py`

Django’s command line entry point for the project.

It is used for tasks such as:

- running the development server
- creating migrations
- applying migrations
- creating a superuser
- running tests

### `db.sqlite3`

The local development database.

Used only for local development and testing, and is ignored from version control.

### `docs/`

This folder contains project documentation, including:

- roadmap
- architecture notes
- data model notes

To make the project easier to understand and maintain as it grows!

## Current data flow

The intended data flow is:

1. financial data is represented through Django models
2. data can be created and edited in Django admin
3. later versions will support CSV import workflows
4. dashboard and analytics views will be built on top of the structured transaction data

For now it is focused on ensuring that the underlying data model is sound before building the user facing analytics layer.

## Design choices so far

### One app for version 1

The project currently uses a single app, `core`, rather than splitting functionality across many apps.

### Django admin as first interface

Django admin is being used as the first usable interface for the project.

This allows early validation of:

- model design
- relationships
- field usability
- data entry workflow

before building custom pages or dashboards.

## Bank-specific import parsing

CSV imports are being designed around bank specific parser functions rather than one generic parser.

The planned approach is:
- one shared import flow in the app
- separate parsing logic for each supported format, such as Lloyds, Santander, and Amex

This keeps bank specific quirks isolated, and makes the import system easier to extend later!

## Expected future expansion

As the project grows, likely additions include:

- CSV transaction import workflow
- transaction cleaning and normalisation logic
- stronger validation rules
- dashboard views and summary pages
- filters and reporting by account, category, and time period

If the scope expands significantly, the project may later introduce additional Django apps for imports or analytics, but this isn't necessary for now.