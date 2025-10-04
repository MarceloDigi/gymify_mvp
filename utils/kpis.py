import streamlit as st

def simple_locale_format(val, fmt="{:,.0f}"):
    # First, format the value using the standard formatter:
    formatted = fmt.format(val)
    # Then swap commas and periods using a temporary placeholder.
    return formatted.replace(",", "TMP").replace(".", ",").replace("TMP", ".")

def compute_kpis(df, agg_map: dict, type_progress: list = None) -> dict:
    if type_progress is not None:
        df = df[df["progress_tracker"].isin(type_progress)].copy()

    result = {}
    for col, agg in agg_map.items():
        if agg == "sum":
            result[col] = float(df[col].sum())
        elif agg == "max":
            result[col] = float(df[col].max())
        elif agg == "min":
            result[col] = float(df[col].min())
        elif agg == "mean":
            result[col] = float(df[col].mean())
        elif agg == "count":
            result[col] = int(df[col].count())
        else:
            raise ValueError(f"Unsupported aggregation method: {agg}")

    return result

def display_kpis(curr: dict, prev: dict, labels: list, mode_dict: dict = None):
    """
    Displays KPIs with deltas. For each KPI, if no previous data is available,
    the delta is shown as "-". Additionally, you can specify via mode_dict whether
    the delta should be absolute or relative (percentage).
    
    Parameters:
      - curr (dict): Current period KPI values.
      - prev (dict): Previous period KPI values.
      - labels (list): List of labels for the KPIs, in the same order as keys in curr.
      - mode_dict (dict, optional): Mapping from KPI keys to display mode,
                                    either "absolute" or "relative".
                                    Defaults to "absolute" if not specified.
    """
    kpi_keys = list(curr.keys())
    cols = st.columns(len(kpi_keys))
    
    for i, col in enumerate(cols):
        key = kpi_keys[i]
        label = labels[i] if i < len(labels) else key
        curr_val = curr[key]
        # Use None if no previous data exists
        prev_val = prev.get(key, None)
        
        # Default mode: absolute.
        mode = "absolute"
        if mode_dict is not None:
            mode = mode_dict.get(key, "absolute")
        
        # Format the current value based on hints from the label.
        if isinstance(curr_val, float):
            if "%" in label:
                value = simple_locale_format(curr_val, "{:,.1f}%")
            elif "kg" in label or "Workload" in label:
                value = simple_locale_format(curr_val, "{:,.0f} kg")
            elif "RM" in label or "Weight" in label:
                value = simple_locale_format(curr_val, "{:,.1f} kg")
            else:
                value = simple_locale_format(curr_val, "{:,.0f}")
        else:
            value = curr_val
        
        # Determine delta:
        # If no previous data is present, show "-"
        if prev_val is None:
            delta = "-"
        else:
            if isinstance(curr_val, (int, float)) and isinstance(prev_val, (int, float)):
                # Use relative mode if specified and previous value is nonzero.
                if mode == "relative" and prev_val != 0:
                    delta_numeric = (curr_val - prev_val) / prev_val * 100
                    # If the label suggests a percentage metric, display a "%" sign.
                    delta = simple_locale_format(delta_numeric, "{:+,.1f}%")
                else:
                    diff = curr_val - prev_val
                    if isinstance(curr_val, float):
                        if "%" in label:
                            delta = simple_locale_format(diff, "{:+,.1f} p.p.")
                        elif "kg" in label or "Workload" in label:
                            delta = simple_locale_format(diff, "{:+,.0f} kg")
                        elif "RM" in label or "Weight" in label:
                            delta = simple_locale_format(diff, "{:+,.1f} kg")
                        else:
                            delta = simple_locale_format(diff, "{:+,.0f}")
                    else:
                        delta = diff
            else:
                delta = "-"
        
        col.metric(label, value, delta, border=True)

def compute_difference_between_kpis(df, kpi_1, kpi_2, drop=False):
    """
    Computes the difference between two KPIs for stacked bar chart.
    """
    df[f'{kpi_1}_vs_{kpi_2}'] = df[kpi_2] - df[kpi_1]
    if drop:
        df.drop(columns=[kpi_2], inplace=True)
    return df