# Finance Journal Entry Template

Use `finance_journal_entries_template.csv` for manual journal entries.

## Columns

- `voucher_no`: One voucher number per journal entry. Use the same value for all debit/credit lines belonging to one entry.
- `entry_date`: Date in `YYYY-MM-DD` format.
- `description`: Voucher-level explanation.
- `line_no`: Line number inside that voucher.
- `account_code`: Use a code from `finance_account_codes_reference.csv`.
- `account_name_optional`: For your readability only.
- `debit_amount`: Debit amount for this line. Use `0` if this is a credit line.
- `credit_amount`: Credit amount for this line. Use `0` if this is a debit line.
- `memo`: Optional line-level note.

## Rules

Each `voucher_no` must balance:

```text
sum(debit_amount) = sum(credit_amount)
```

Every voucher should have at least two lines: one debit and one credit.

## Common Examples

Owner puts money into business:

```text
DR 1100 Cash and Bank
CR 3000 Owner's Equity
```

Pay an expense by bank/cash:

```text
DR 5100 Operating Expenses
CR 1100 Cash and Bank
```

Receive other income:

```text
DR 1100 Cash and Bank
CR 4100 Other Income
```

Vendor bill not entered through purchase module:

```text
DR 5100 Operating Expenses or 1300 Inventory Asset
CR 2000 Accounts Payable
```
