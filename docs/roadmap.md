# Roadmap

## Current stage

I'm currently in the foundation phase of this project.

So far, the focus has been on:
- setting up the Django project properly
- creating the first `core` app
- building the initial data model
- registering models in Django admin
- adding basic model tests
- documenting the structure and data model
- Lloyds CSV import now supports upload, preview, and confirm import; next focus is duplicate protection and import UX improvements

## Short-term next steps

These are the next things to build:

- improve model validation
- tidy and expand project documentation
- design a simple CSV import workflow
- add a basic homepage / dashboard view
- start building useful summary queries from transaction data

## Version 1 goal

The goal of version 1 is a usable personal finance tracker that can:

- store accounts, categories, and transactions
- support personal and joint spending
- allow transactions to be entered or imported
- support categorisation and filtering
- provide basic summaries and dashboard-style insights

## Likely future improvements

Once the basics are working well, future improvements could include:

- better transaction validation rules
- merchant normalisation
- duplicate detection on import
- more detailed category structures
- recurring transaction support
- savings goals or budgeting features
- cleaner dashboard and analytics views

## Guiding principle

The aim is not to build every possible finance feature upfront.

The aim is to build:
- a clean foundation
- a useful personal tool
- a strong learning project
- a portfolio-worthy codebase

New features will only be added if they improve the project without making the structure messy.