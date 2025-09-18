import plotly.graph_objects as go
import pandas as pd
import streamlit as st

labels = [
        "📅 Días entrenados",
        "🏋️ Series hechas",
        "✅ Series efectivas",
        "📈 % Series efectivas",
        "📦 Workload total",
        "🏋️ Max. 1 RM",
        "💪 Max. Peso",
    ]

primary_color = '#fa9f3d'
secondary_color = '#656566'

def plot_line_vs_bar(df, 
                     col_line: str, 
                     col_bars,  # Can be str or list of str
                     data_labels: list = [None, None], # [y1 label, y2 label] or None
                     color_line=primary_color, 
                     colors_bars=None,
                     axis_color: bool = True, 
                     showline: bool = False,
                     show_labels="none" # "all", "line", "bars", "none", or list of columns
                     ):
    """
    Plots a combined bar (can be stacked) and line chart with dual y-axes.

    Parameters:
      - df (pd.DataFrame): Must include a 'fecha' column.
      - col_line (str): Column to be used for the line (y-axis 2).
      - col_bars (str or list): One or more columns to be stacked as bars (y-axis 1).
      - color_line (str): Line color (y-axis 2).
      - colors_bars (list): Colors for bars (should match length of col_bars if provided).
      - axis_color (bool): If True, axes are colored like their data series. If False, white.
      - showline (bool): Show axis lines.
      - show_labels: "all", "line", "bars", "none", or list of col_bars to show labels on.
    """
    if len(data_labels) < 2:
        data_labels.append(None)

    if isinstance(col_bars, str):
        col_bars = [col_bars]

    if colors_bars is None:
        colors_bars = [secondary_color, "#fb8072", "#80b1d3", "#fdb462"]  # Default color palette

    # Assign axis colors
    axis_color1 = colors_bars[0] if axis_color else "#ffffff"
    axis_color2 = color_line if axis_color else "#ffffff"

    # Titles
    def format_title(col):
        title = str.capitalize(col.replace("_", " "))
        if any(kw in col.lower() for kw in ['1rm', 'weight', 'workload']):
            title += ' (kg)'
        return title

    data_labels[1] = format_title(col_line)
    if data_labels[0] is None:
        data_labels[0] = format_title(col_bars[0])

    fig = go.Figure()

    # Determine logic for bar label display
    bar_label_cols = []
    if show_labels == "all":
        bar_label_cols = col_bars
        line_labels = True
    elif show_labels == "bars":
        bar_label_cols = col_bars
        line_labels = False
    elif show_labels == "line":
        bar_label_cols = []
        line_labels = True
    elif isinstance(show_labels, list):
        bar_label_cols = show_labels
        line_labels = False
    else:
        bar_label_cols = []
        line_labels = False

    # Add stacked bars
    for i, col in enumerate(col_bars):
        fig.add_bar(
            x=df["fecha"],
            y=df[col],
            name=col_bars[i],
            yaxis="y1",
            marker_color=colors_bars[i % len(colors_bars)],
            text=df[col] if col in bar_label_cols else None,
            textposition="auto" if col in bar_label_cols else None
        )

    # Add line on secondary axis
    fig.add_trace(go.Scatter(
        x=df["fecha"],
        y=df[col_line],
        name=data_labels[1],
        mode="lines+markers+text" if line_labels else "lines+markers",
        yaxis="y2",
        line=dict(color=color_line),
        text=df[col_line] if line_labels else None,
        textposition="top center" if line_labels else None
    ))

    fig.update_layout(
        barmode="stack",
        title=f"{data_labels[1]} vs. {data_labels[0]}",
        xaxis=dict(showgrid=False),
        yaxis=dict(
            title=data_labels[0],
            side="left",
            showgrid=False,
            showline=showline,
            linecolor=axis_color1,
            tickfont=dict(color=axis_color1),
            title_font=dict(color=axis_color1),
            rangemode='tozero'
        ),
        yaxis2=dict(
            title=data_labels[1],
            overlaying="y",
            side="right",
            showgrid=False,
            showline=showline,
            linecolor=axis_color2,
            tickfont=dict(color=axis_color2),
            title_font=dict(color=axis_color2),
            rangemode='tozero'
        ),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        margin=dict(t=40, b=40),
        height=400
    )

    st.plotly_chart(fig, use_container_width=True, config={
    "staticPlot": True,
    "displayModeBar": False
    })

def display_exercise_tags(exercises):
    st.subheader("🏷️ Ejercicios incluidos en el análisis")
    tags = [
        f"<span style='background-color:{primary_color};border-radius:10px;padding:5px 10px;margin:5px;display:inline-block'>{e}</span>"
        for e in sorted(exercises)
    ]
    st.markdown(" ".join(tags), unsafe_allow_html=True)

def plot_muscle_analysis(data, 
                         x1_col, 
                         y_col, 
                         x1_label, 
                         title, 
                         x2_col=None, 
                         x2_label=None, 
                         color1=primary_color, 
                         color2=secondary_color,
                         data_labels: list = [True, False],
                         custom_data_labels: list = [None, None],
                         data_prefix: list = [False, False],
                         hide_xaxis: bool = False,
                         x1_suffix: str = "",
                         x2_suffix: str = ""):
    """
    Plots a horizontal bar chart for muscle analysis, supporting one or two values,
    with an option to hide the x-axis and to append suffixes and optionally add a dynamic
    prefix (a plus sign) for positive values.
    
    Parameters:
        data (pd.DataFrame): The data to plot.
        x1_col (str): Column name for the first bar (e.g., series counter).
        y_col (str): Column name for the y-axis (e.g., muscle ID).
        x1_label (str): Label for the first bar.
        title (str): Title of the chart.
        x2_col (str, optional): Column name for the second bar.
        x2_label (str, optional): Label for the second bar (required if x2_col is provided).
        color1 (str): Color for the first bar.
        color2 (str): Color for the second bar.
        data_labels (list): A list with booleans for displaying data labels for each bar.
                            For example, [True, False] means show label for first bar and hide for second.
        custom_data_labels (list): A list with custom data labels for each bar.
        data_prefix (list): A list with booleans to decide whether to add a dynamic "+" prefix to the value for each bar.
                            For example, [True, False] adds the plus only to the first bar's labels.
        hide_xaxis (bool): If True, hides the x-axis.
        x1_suffix (str): Suffix to append to each data label in the first bar.
        x2_suffix (str): Suffix to append to each data label in the second bar.
    """
    # Ensure data_labels and data_prefix have at least 2 elements if x2_col is provided:
    if x2_col:
        if len(data_labels) < 2:
            raise ValueError("When x2_col is provided, data_labels must have at least two elements.")
        if len(data_prefix) < 2:
            raise ValueError("When x2_col is provided, data_prefix must have at least two elements.")
        
    # Sort data for consistent visualization
    sort_columns = [x1_col] if not x2_col else [x1_col, x2_col]
    sorted_data = data.sort_values(by=sort_columns)

    # Create the figure
    fig = go.Figure()

    # Prepare text for first bar with suffix if data_labels enabled
    if data_labels[0]:
        if custom_data_labels[0] is not None:
            text_x1 = [f"{'+' if data_prefix[0] and val > 0 else ''}{val}{x1_suffix}" for val in sorted_data[custom_data_labels[0]]]
        else:
            text_x1 = [f"{'+' if data_prefix[0] and val > 0 else ''}{val}{x1_suffix}" for val in sorted_data[x1_col]]
    else:
        text_x1 = None

    # Add the first bar
    fig.add_bar(
        x=sorted_data[x1_col],
        y=sorted_data[y_col],
        name=x1_label,
        orientation='h',
        marker_color=color1,
        text=text_x1,
        textposition='auto',
    )

    # Add the second bar if x2_col is provided
    if x2_col:
        if not x2_label:
            raise ValueError("x2_label must be provided if x2_col is specified.")
        
        if data_labels[1]:
            if custom_data_labels[1] is not None:
                text_x2 = [f"{'+' if data_prefix[1] and val > 0 else ''}{val}{x2_suffix}" for val in sorted_data[custom_data_labels[1]]]
            else:
                text_x2 = [f"{'+' if data_prefix[1] and val > 0 else ''}{val}{x2_suffix}" for val in sorted_data[x2_col]]
        else:
            text_x2 = None

        fig.add_bar(
            x=sorted_data[x2_col],
            y=sorted_data[y_col],
            name=x2_label,
            orientation='h',
            marker_color=color2,
            text=text_x2,
            textposition='auto',
        )

    # Update layout
    fig.update_layout(
        title=title,
        xaxis_title="Count",
        yaxis_title="Muscle",
        barmode='stack' if x2_col else None,  # Use stacked bars if two values are plotted
        height=600,
        margin=dict(t=40, b=40, l=40, r=40),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
    )

    # Optionally hide the x-axis
    if hide_xaxis:
        fig.update_xaxes(visible=False)

    # Display the chart in Streamlit
    st.plotly_chart(fig, use_container_width=True, config={
    "staticPlot": True,
    "displayModeBar": False
    })