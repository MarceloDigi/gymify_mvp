import pandas as pd
import numpy as np
import streamlit as st

weight_body_exercises = [
    'Chin-ups', 
    'Parallel bar dips',
    'Pull-ups',
    'Muscle-ups',
    'Neutral grip pull-ups',
    'Ring chin-ups',
    'Parallel bar dips 210',
    'Barbell squat'
    ]

def snake_case(df):
    df.columns = df.columns.str.lower().str.replace(' ','_')

def drop_empty_rows(df, fecha_col: str = 'fecha'):
    df.dropna(axis=0, how='all') # Elinimaos filas donde todos los valores son nulos
    df.drop(df[df[fecha_col].isnull()].index, inplace=True) # Eliminamos filas donde la fecha es nula (just in case)
    return df

def convert_date_columns(df, 
                         date_columns: list = ['fecha'], 
                         multiple_formats=False, 
                         desired_format='%Y-%m-%d') -> pd.DataFrame:
    """
    Converts specified columns in a DataFrame to datetime format.

    Parameters:
        df (pd.DataFrame): The input DataFrame.
        date_columns (list): List of column names to convert to datetime.
        multiple_formats (bool): Indicate if there are multiple columns within the same column.
        desired_format (str): Format used by default.

    Returns:
        pd.DataFrame: DataFrame with converted date columns.
    """
    if multiple_formats == False:
        if len(date_columns) == 1:
            date_columns = date_columns[0]
        df[date_columns] = df[date_columns].apply(pd.to_datetime, format=desired_format)
    else:
        for col in date_columns:
            df['fecha_1'] = pd.to_datetime(df[col], format='%Y - %m', errors='coerce')
            df['fecha_2'] = pd.to_datetime(df[col], format='%Y - %m - %d', errors='coerce')
            df['fecha_3'] = pd.to_datetime(df[col], format='%Y-%m-%d', errors='coerce')
            df[col] = df[['fecha_1','fecha_2','fecha_3']].max(1)
            df.drop(['fecha_1', 'fecha_2','fecha_3'], axis=1, inplace=True)

    return df

def convert_right_formats(df, 
                          int_cols=None, 
                          float_cols=None,
                          str_cols=None):
    # Right formats
    pd.set_option('future.no_silent_downcasting', True)

    df = df.replace('',np.nan)
    if str_cols is not None:
        df[str_cols] = df[str_cols].apply(lambda x: x.str.strip())
    if float_cols is not None:
        df[float_cols] = df[float_cols].astype(float)
    if int_cols is not None:
        df[int_cols] = df[int_cols].astype("Int64")

    return df

def basic_cleanings(df: pd.DataFrame, 
                    date_columns: list = None,
                    str_cols: list = None, 
                    int_cols: list = None, 
                    float_cols: list = None,
                    drop_cols: list = None,
                    order_cols: list = None,
                    rename_cols: dict = None):
    
    snake_case(df)
    df = drop_empty_rows(df)

    if date_columns is not None:
        df = convert_date_columns(df, date_columns=date_columns)
    if int_cols is not None or float_cols is not None or str_cols is not None:
        df = convert_right_formats(df, int_cols=int_cols, float_cols=float_cols, str_cols=str_cols)
    if rename_cols is not None:
        df.rename(columns=rename_cols, inplace=True)
    if drop_cols is not None:
        df.drop(drop_cols, axis=1, inplace=True)
    if order_cols is not None:
        df = df[order_cols]
        
    return df

def range_col_cleaning(df):
    """
    Clean and split the range column into repmin, repmax and technique.
    """
    # Range column
    if 'rango' in df.columns:
        range_sep = df['rango'].str.split(' - ', expand=True).rename(columns={0: 'repmin', 1: 'repmax'})
        df = pd.concat([df, range_sep], axis=1).drop(columns=['rango'])
    return df

def rep_concatenate(df, 
                    repmin_col: str = "repmin", 
                    repmax_col: str = "repmax", 
                    exercise_col: str = 'exercise',
                    drop=True, 
                    weight_body_exercises: list = weight_body_exercises):
    """
    Combines min and max rep values into a single 'reprange' column for readability.
    Handles Myo/Dropset tags and gracefully deals with missing or malformed data.
    Drops original columns after processing.
    """
    if repmin_col not in df.columns or repmax_col not in df.columns:
        st.warning(f"Columns '{repmin_col}' or '{repmax_col}' not found. Returning DataFrame unchanged.")
        return df

    def format_number(x):
        try:
            x_float = float(x)
            return str(int(x_float)) if x_float == int(x_float) else str(x_float)
        except (ValueError, TypeError):
            return str(x) if pd.notna(x) else ""

    pd.set_option('future.no_silent_downcasting', True)
    df[['repmax','repmin']] = df[['repmax','repmin']].replace('',np.nan)
    try:
        df["reprange"] = np.where(
                        (df[repmin_col].isin(['Myoreps', 'Dropset'])) | (df[repmin_col].isnull()),
                        df[repmin_col],
                            np.where(
                            (df[repmin_col] == -1) & (df[exercise_col].isin(weight_body_exercises)),
                            'AMRAP',
                                np.where(
                                (df[repmin_col] == -1) & (~df[exercise_col].isin(weight_body_exercises)),
                                'Dropset',
                                    np.where(
                                    df[repmax_col].isnull(),
                                    df[repmin_col].apply(format_number),
                                        df[repmin_col].apply(format_number) + " - " + df[repmax_col].apply(format_number)
                                    )
                                )
      
                            )
                        )
                                
        if drop:
            df.drop(columns=[repmin_col, repmax_col], inplace=True)
    except Exception as e:
        st.error(f"Error concatenating rep range: {e}")
    return df

def repmin_cleaning(df):
    """
    Clean the repmin column into technique and repmin numeric.
    """
    # Technique column and repmin cleaning
    if pd.api.types.is_string_dtype(df['repmin']):
        df["technique"] = df["repmin"].where(df["repmin"].str.isalpha())
    else:
        df["technique"] = np.nan

    df['repmin'] = pd.to_numeric(df['repmin'], errors='coerce')
    
    return df