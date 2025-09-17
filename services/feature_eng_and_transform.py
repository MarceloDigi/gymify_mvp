import pandas as pd
import numpy as np

def merge_muscleroles_and_dwh(df, df_muscleroles):
    """
    Merge muscle roles with workout data
    Parameters:
        df: DataFrame with workout data
        df_muscleroles: DataFrame with muscle roles data
    Returns:
        df_by_muscle: DataFrame with merged data
    """
    df_muscleroles = df_muscleroles.replace('',np.nan)
    df_muscleroles['english_name'] = df_muscleroles.english_name.str.capitalize()
    ss_muscleroles = df_muscleroles[['muscle_name','rol','english_name','rol_multiplier']].copy()

    if 'id_serie' not in df.columns:
        df.reset_index(names='id_serie', inplace=True)

    # Merge
    df_by_muscle = df.merge(ss_muscleroles, how='left', left_on='exercise', right_on='english_name').drop(['english_name'], axis=1)
    
    return df_by_muscle