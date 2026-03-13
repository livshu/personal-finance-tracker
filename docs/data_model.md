# Data Model

## Overview

Version 1 of the project is built around three core models:

- `Account`
- `Category`
- `Transaction`

The main one is `Transaction`. The other two give it context.

This setup is meant to support:
- personal and joint finance tracking
- income and spending categories
- manual entry now, CSV imports later
- dashboards and analysis later on

## `Account`

`Account` = where money lives or moves through.

Examples:
- current account
- savings account
- credit card
- joint account
- cash

Fields:
- `name`
- `account_type`
- `owner_type`
- `institution`
- `currency`
- `notes`

This lets the app answer things like:
- which account a transaction came from
- spending by account
- personal vs joint spending

## `Category`

`Category` is how transactions are grouped.

Examples:
- Salary
- Groceries
- Rent
- Transport

Fields:
- `name`
- `parent`
- `is_income`
- `description`

Without categories, you only get total money in and out. With them, you can later look at:
- spending by category
- biggest spending areas
- income vs expenses

### Parent categories

The `parent` field is optional and allows category grouping.

Example:
- Food
  - Groceries
  - Eating Out

This gives flexibility later without making version 1 too complicated.

## `Transaction`

`Transaction` is the core record in the app. It represents one money event.

Examples:
- salary payment
- grocery shop
- rent payment
- refund
- transfer

Fields:
- `account`
- `category`
- `date`
- `amount`
- `description_raw`
- `merchant_normalized`
- `transaction_type`
- `source_file`
- `imported_at`
- `notes`
- `is_transfer`
- `is_excluded`

Why it exists:
This is the table that future imports, summaries, and dashboards will all rely on.

It stores:
- when something happened
- how much it was
- whether it was money in or out
- which account it belongs to
- how it should be categorised
- whether it should be treated differently in analysis

## Relationships

Current relationships are:

- one `Account` can have many `Transaction`s
- one `Category` can have many `Transaction`s
- one `Category` can have child categories

### Delete behaviour

- deleting an `Account` deletes its transactions
- deleting a `Category` does not delete transactions; their category just becomes blank
- deleting a parent `Category` does not delete child categories; their parent just becomes blank

That was done to preserve transaction data where possible.

## Key design choices

### Transaction-first model

The project is built around transactions because that is what dashboards and analysis will ultimately use.

### Positive amounts + separate direction

`amount` is stored as a positive decimal value, and direction is stored separately in `transaction_type` (`debit` or `credit`).

This keeps version 1 simpler and avoids confusion around signed values during imports.

### Decimal for money

`amount` uses `DecimalField` rather than float, which is the right choice for financial data.

### Category is optional

A transaction can exist without a category. That is useful for future imports where transactions may come in uncategorised first.

### Raw vs cleaned merchant text

Both are stored:
- `description_raw` keeps the original text
- `merchant_normalized` gives room for cleaner analysis later

### Transfer and exclusion flags

These are there so later summaries can treat some transactions differently without deleting them.

Examples:
- transfers should usually not count as spending
- excluded rows should stay in the database but stay out of reporting

## Current limitations


Version 1 now includes basic validation to stop obvious mismatches between transaction direction and category type.

For example:
- `credit` transactions cannot use non-income categories
- `debit` transactions cannot use income categories

There are still areas not yet enforced, for example:
- transfer logic is only partially modelled
- duplicate detection is not implemented yet
- split transactions are not supported yet
- recurring transactions are not supported yet
- duplicate detection is not implemented yet
- split transactions are not supported yet
- recurring transactions are not supported yet

