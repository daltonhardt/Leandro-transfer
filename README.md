# This a simple App to control Income and Expenses using Streamlit and Google Sheets API

## It has only 2 menu options:
## New record
## Result


### New record
- Allows you to enter Date, Description, Value and Type (Income/Expense).
- Data is stored (appended) in Google Sheets in corresponding Worksheet according to Month extracted from date input.


### Result
- Displays the Incomes, Expenses and Balance Metrics of the month or selected period (there is a multiselet option to choose from Jan to Dec).
- It also shows dataframe tables of Incomes & Expenses, Only Incomes, Only Expenses all in chronological order
