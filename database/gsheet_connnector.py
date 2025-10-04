import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import os

def get_gsheet_credentials():
    """
    Get Google Sheets credentials.
    """
    path1 = os.getenv("GOOGLE_CREDENTIALS_PATH")
    path2 = os.getenv("GOOGLE_CREDENTIALS_PATH_OTHER")

    if path1 and os.path.exists(path1):
        CREDENTIALS_PATH = path1
    elif path2 and os.path.exists(path2):
        CREDENTIALS_PATH = path2
    else:
        raise FileNotFoundError("No se encontraron credenciales válidas.")

    scope = [
    "https://spreadsheets.google.com/feeds",
    "https://www.googleapis.com/auth/drive"
    ]

    creds = ServiceAccountCredentials.from_json_keyfile_name(CREDENTIALS_PATH, scope)
    client = gspread.authorize(creds)

    return client

def read_gsheet(spreadsheet_key: str = None, worksheet: str = None) -> pd.DataFrame:
    client = get_gsheet_credentials()
    key = os.getenv(spreadsheet_key)
    spreadsheet = client.open_by_key(key)

    worksheet_open = spreadsheet.worksheet(worksheet)
    worksheet_open = worksheet_open.get_all_records()
    df_worksheet = pd.DataFrame.from_records(worksheet_open)

    return df_worksheet
                                         
def dump_data_into_gsheet(spreadsheet, worksheet_name: str, df: pd.DataFrame):
    """
    Dump a DataFrame into a Google Sheet.
    """
    # Convert DataFrame to list of lists
    data = [df.columns.tolist()] + df.values.tolist()

    # Update the worksheet with the new data
    spreadsheet.values_update(
        worksheet_name,
        params={'valueInputOption': 'USER_ENTERED'},
        body={'values': data}
    )