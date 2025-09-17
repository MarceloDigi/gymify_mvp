import numpy as np
import pandas as pd
import streamlit_dashboard.services.datawrangling as dw

sql_hypertrophy['id_user'] = np.nan
templates_test['id_user'] = np.nan    
sql_routines['last_change'] = pd.to_datetime(sql_routines['last_change'])

def routine_templates_to_oltp(templates_olap, sql_routines, sql_exercises, sql_routinetemplates, sql_hypertrophy):
    """
    Converts the routine templates from OLAP to OLTP format.
    """
    templates_olap_merged = templates_olap.merge(
                                sql_routines.sort_values(by='last_change', ascending=False)\
                                    .drop_duplicates(subset=['id_user','routine_name','is_active'], keep='first')\
                                        [['id_user','id_routine','routine_name']], 
                                            how='left', 
                                            on=['id_user','routine_name'])

    templates_olap_merged = templates_olap_merged.merge(
                                sql_exercises[['id_exercise','english_name']], 
                                    how='left', 
                                    left_on='exercise', 
                                    right_on='english_name') 

    templates_olap_merged.drop(['routine_name','english_name','exercise'], axis=1, inplace=True)

    templates_olap_merged['weight_predefined'] = np.nan
    templates_olap_merged['rir_predefined'] = np.nan
    templates_olap_merged['pct_strenght'] = np.nan

    # Clean the rep min column (the hypertrophy techniques)
    templates_olap_merged = dw.clean_repmin_hypertrophy(templates_olap_merged)
    templates_olap_merged = templates_olap_merged.merge(sql_hypertrophy, on=['id_user','hypertrophy_name'], how='left')

    # Add the id column
    max = sql_routinetemplates.id_set_routine_template.max() + 1
    index_id = np.arange(max, max + len(templates_olap_merged))
    templates_olap_merged['id_set_routine_template'] = index_id
    
    templates_olap_merged = templates_olap_merged[sql_routinetemplates.columns]

    return templates_olap_merged