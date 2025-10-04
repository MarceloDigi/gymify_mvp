# utils/styling.py
import streamlit as st

def texto_periodo_seleccionado(start_date, end_date, prev_start, prev_end, period_length):
    string = f"""
        <div style='color: rgba(213, 212, 213,0.5); font-size: 0.9rem;'>
            <strong>Periodo seleccionado:</strong> {start_date.strftime('%d %b %Y')} — {end_date.strftime('%d %b %Y')} ({period_length} días)
            <br>
            <strong>Comparando con:</strong> {prev_start.strftime('%d %b %Y')} — {prev_end.strftime('%d %b %Y')}
        </div>
        """
    return st.markdown(string, unsafe_allow_html=True)
    