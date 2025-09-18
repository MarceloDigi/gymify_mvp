import pandas as pd
import numpy as np
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import sys
import os
import services.datawrangling as dw

def read_gsheet(spreadsheet, worksheet_name: str):
    sheet = spreadsheet.worksheet(worksheet_name)
    records = sheet.get_all_records()
    df = pd.DataFrame.from_records(records)
    return df

# Read the Workout Templates
def read_and_clean_sheet(spreadsheet_fitness_personal, worksheet_name: str, date_cols: list = None):
    df = read_gsheet(spreadsheet_fitness_personal, worksheet_name)
    dw.snake_case(df)
    df = df.replace('',np.nan)

    cols = ['routine_name','sets_order','exercise','rep_min','rep_max']
    if all(cols) in df.columns:
        df = df[cols]

    if 'i/o' in df.columns:
        df.drop('i/o', axis=1, inplace=True)

    if date_cols is not None:
        df = dw.convert_date_columns(df, date_columns=date_cols)
        df = dw.drop_empty_rows(df, fecha_col=date_cols[0])

    return df

def load_data_into_gsheet(spreadsheet, worksheet_name: str, df: pd.DataFrame):
    """
    Load a DataFrame into a Google Sheet.
    """
    # Convert DataFrame to list of lists
    data = [df.columns.tolist()] + df.values.tolist()

    # Update the worksheet with the new data
    spreadsheet.values_update(
        worksheet_name,
        params={'valueInputOption': 'USER_ENTERED'},
        body={'values': data}
    )

def get_gsheet_credentials():
    """
    Get Google Sheets credentials.
    """
    CREDENTIALS_PATH = os.getenv("GOOGLE_CREDENTIALS_PATH")

    scope = [
    "https://spreadsheets.google.com/feeds",
    "https://www.googleapis.com/auth/drive"
    ]

    creds = ServiceAccountCredentials.from_json_keyfile_name(CREDENTIALS_PATH, scope)
    client = gspread.authorize(creds)

    return client
