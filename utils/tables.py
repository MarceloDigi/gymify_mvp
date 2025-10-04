import pandas as pd
import numpy as np
import streamlit as st

def simple_locale_format(val, fmt="{:,.0f}"):
    # First, format the value using the standard formatter:
    formatted = fmt.format(val)
    # Then swap commas and periods using a temporary placeholder.
    return formatted.replace(",", "TMP").replace(".", ",").replace("TMP", ".")

def highlight_deltas(val):
    if pd.isna(val): return ''
    color = 'lightgreen' if val > 0 else 'salmon' if val < 0 else 'lightgray'
    return f'color: {color}'

def render_day_table(df, **metrics):
    agg = df.groupby("fecha").agg(metrics).reset_index()

    if 'Series Efectivas' in agg.columns and 'Total Series' in agg.columns:
        agg["%_series_efectivas"] = (agg['Series Efectivas'] / agg['Total Series']) * 100
        agg.drop('Series Efectivas', axis=1, inplace=True)
    
    agg["fecha"] = agg["fecha"].dt.strftime("%Y-%m-%d")

    st.subheader("📆 Detalle diario")
    st.dataframe(agg.style.format({
        "workload_total": "{:,.0f}",
        "%_series_efectivas": "{:.0f}%",
        "max_1rm": "{:.1f}"
    }))

def double_grouping(df, groupers: list, metrics, filter=None):
    """
    Performs double grouping on a DataFrame.
    Parameters:
        df (pd.DataFrame): DataFrame to group.
        groupers (list): List of columns to group by.
        metrics (dict): Dictionary of metrics to aggregate.
        filter (pd.Series, optional): Boolean mask for filtering the DataFrame.
    """
    if filter is not None:
        df = df[filter]

    df1 = df.groupby(groupers) \
        .agg(metrics).reset_index()
    
    key = list(metrics)[1]
    metrics[key] = 'sum'

    df2 = df1.groupby(groupers[0]) \
        .agg(metrics).reset_index()
    
    metrics[key] = 'max'
    
    return df2

def calculate_summary_table(df_now, group_col, metrics, df_prev=None, compare_prev=True):
    """
    Calculates the summary table with deltas between current and previous data.

    Parameters:
        df_now (pd.DataFrame): Current period data.
        df_prev (pd.DataFrame): Previous period data.
        group_col (str): Column to group by (e.g., "id_muscle").
        metrics (dict): Metrics to aggregate (e.g., {"workload": ("workload", "sum")}).
        compare_prev (bool): Whether to compare with previous data.

    Returns:
        pd.DataFrame: Merged table with calculated deltas.
    """
    # Aggregate current data
    agg_now = df_now.groupby(group_col).agg(**metrics).reset_index()
    if 'Series Efectivas' in agg_now.columns and 'Total Series' in agg_now.columns:
        agg_now["%_series_efectivas"] = (agg_now['Series Efectivas'] / agg_now['Total Series']) * 100
    
    df = agg_now.copy()
    
    if compare_prev:
        # Aggregate previous data
        agg_prev = df_prev.groupby(group_col).agg(**metrics).reset_index()
        if 'Series Efectivas' in agg_prev.columns and 'Total Series' in agg_prev.columns:
            agg_prev["%_series_efectivas"] = (agg_prev['Series Efectivas'] / agg_prev['Total Series']) * 100

        # Merge current and previous data
        merged = pd.merge(agg_now, agg_prev, on=group_col, how="left", suffixes=("", "_prev"))

        # Calculate deltas
        for col in agg_now.columns:
            if col != group_col and col in agg_prev.columns:
                delta_col = f"Δ_{col}"
                if "workload" in col.lower():
                    merged[delta_col] = (merged[col] / merged[f"{col}_prev"] - 1) * 100
                else:
                    merged[delta_col] = merged[col] - merged[f"{col}_prev"]
        
        df = merged.copy()

    # Fill NaN values with 0
    df.fillna(0, inplace=True)

    if 'fecha' in df.columns:
        df["fecha"] = df["fecha"].dt.strftime("%Y-%m-%d")

    # Format numeric columns (excluding delta columns and the group column)
    for col in df.columns:
        if col == group_col:
            continue
        elif "rm" in col.lower() or "weight" in col.lower():
            df[col] = df[col].round(1).astype(float)
        else:
            df[col] = df[col].round(0).astype(int)

    return df

def display_summary_table(df, group_col, title, custom_formats: dict = None):
    """
    Displays the summary table in Streamlit with formatting.
    
    Parameters:
        df (pd.DataFrame): The merged table with deltas.
        group_col (str): Column to group by (e.g., "id_muscle").
        title (str): Title of the table to display.
        custom_formats (dict, optional): A dictionary mapping column names to format strings.
                                         For any column not specified here, the default format
                                         will be "{:,.0f}".
    """
    # Base default formatting rules
    format_dict = {
        "workload_total": "{:,.0f}",
        "%_series_efectivas": "{:.0f}%"
    }
    
    # If the user provided custom_formats, override or add these formats.
    if custom_formats is not None:
        for col, fmt in custom_formats.items():
            format_dict[col] = fmt

    # Loop over all columns not yet explicitly set, except the group column,
    # and apply default formatting.
    for col in df.columns:
        # For delta columns we may want a special format:
        if col.startswith("Δ"):
            if "workload" not in col.lower() and "%" not in col:
                format_dict[col] = lambda x, fmt="{:+,.0f}": simple_locale_format(x, fmt)
            else:
                format_dict[col] = lambda x, fmt="{:+,.0f}%": simple_locale_format(x, fmt)
        # For other columns (not group_col) that haven't been specified, use default.
        elif col not in format_dict and col != group_col:
            format_dict[col] = lambda x, fmt="{:,.0f}": simple_locale_format(x, fmt)

    # Apply formatting and then apply highlight function to delta columns.
    df.set_index(group_col, inplace=True)

    # Reorder columns
    ordered = []
    for col in df.columns:
        if col == group_col or col.startswith("Δ"):
            continue
        ordered.append(col)
        delta_col = f"Δ_{col}"
        if delta_col in df.columns:
            ordered.append(delta_col)
            
    df = df[ordered]

    styled = df.style.format(format_dict)
    styled = styled.map(highlight_deltas, subset=[col for col in df.columns if col.startswith("Δ")])

    # Display the styled table in Streamlit.
    st.subheader(title)
    st.dataframe(styled)

def reformat_historical_routine_for_display(df):
    """
    Process the historical routine DataFrame to prepare it for display.
    Renames columns, formats dates, and calculates height for display.
    """
    new_columns = {
        'fecha':'Fecha',
        'exercise':'Ejercicio',
        'reprange':'Rango',
        'repreal':'Reps',
        'weight':'Peso',
        'rir':'RIR'
    }
    df.rename(columns=new_columns, inplace=True)
    df['Fecha'] = df['Fecha'].dt.strftime('%Y-%m-%d')
    columns_to_show = ['Ejercicio','Rango','Reps','Peso','RIR']
    columns_to_show = [col for col in columns_to_show if col in df.columns]

    row_height = 35  # Approx row height in pixels
    num_rows = df.shape[0]
    height = 100 + num_rows * row_height  # 100 for header padding

    return df, columns_to_show, height

def editable_dataframe(df_template, ejercicio, idx):
    """
    Create an editable DataFrame for a specific exercise.
    If the exercise is not found in the template, create a default DataFrame.

    Parameters:
        df_template (pd.DataFrame): The template DataFrame containing exercise data.
        ejercicio (str): The selected exercise.
        idx (int): The index of the exercise in the template.
    Returns:
        pd.DataFrame: An editable DataFrame for the selected exercise.
    """
    if ejercicio in df_template['exercise'].values:
        # Filter the DataFrame to only include the selected exercise
        df_filtered = df_template.loc[df_template['exercise'] == ejercicio,['exercise','reprange']].copy()
        df_filtered['reps_real'] = 0
        df_filtered['weight'] = 0.0
        df_filtered['rir'] = np.nan
    else:
        default_rows = 4
        df_filtered = pd.DataFrame(
            {
            'exercise': [ejercicio] * default_rows,
            'reprange': [np.nan] * default_rows,
            'reps_real': [0] * default_rows, 
            'weight': [0.0] * default_rows, 
            'rir': np.nan * default_rows}
        )
    new_names = {
        'exercise':'Ejercicio',
        'reprange':'Rango',
        'reps_real':'Reps',
        'weight':'Peso',
        'rir':'RIR'
    }
    df_filtered.rename(columns=new_names, inplace=True)
    df_filtered.reset_index(inplace=True, drop=True)
    
    edited_df = st.data_editor(
                            df_filtered, 
                            disabled=('Ejercicio'), 
                            key=f"editor_{ejercicio}_{idx}", 
                            num_rows="dynamic")

    return edited_df