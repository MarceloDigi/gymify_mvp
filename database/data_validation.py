import pandas as pd
import numpy as np
import streamlit as st
from datetime import datetime
import re

eh_techniques = ['Myo-reps', 'Parciales', 'Dropset', 'Rest-pause', 'Clúster']

def clean_rango(value):
    """
    Clean and format the 'Rango' column.
    Handles ranges, single numbers, and specific techniques.
    """
    if pd.isna(value):
        return ""

    val = str(value).strip()

    # Detectar todos los números
    nums = re.findall(r"\d+(?:\.\d+)?", val)
    if len(nums) == 2:
        a, b = sorted(map(float, nums))
        return f"{a:g} - {b:g}"

    # Número suelto válido
    try:
        float(val)
        return val
    except ValueError:
        pass

    # Técnica en formato title
    return val.lower().title()

def is_valid_rango(val):
    """
    Check if the 'Rango' value is valid.
    Validates if it's a number, a range, or a recognized technique.
    Returns True if valid, False otherwise.
    """
    if pd.isna(val) or val == "":
        return True

    val_str = str(val).strip()

    # Si contiene números, es válido
    if re.search(r"\d", val_str):
        return True

    # Si es texto, verificar si es una técnica válida
    return val_str.lower().capitalize() in eh_techniques

def validate_current_routine(df):
    """
    Validate the current routine data.
    Checks for empty sets, invalid RIR values, high weights, and unusual rep/peso combinations.
    Returns a cleaned DataFrame if all validations pass.
    """
    # Crear columna de fecha y reordenarla
    today = datetime.now().strftime('%Y-%m-%d')
    df['fecha'] = today
    df = df[['fecha','Ejercicio','Rango','Reps','Peso','RIR']]

    # Definir columnas de entrada y numéricas
    input_cols = ['Reps', 'Peso', 'RIR']
    numeric_cols = ['Reps', 'Peso']
    hypertrophy_techniques = ['Myo-reps', 'Parciales', 'Dropset', 'Rest-pause', 'Clúster']

    # Quitar sets vacíos
    df = df[df[numeric_cols].sum(axis=1) != 0]
    # Validación de inputs
    st.subheader("Validación de la rutina")

    # Inicializar estados
    if "confirmed_null_rir" not in st.session_state:
        st.session_state["confirmed_null_rir"] = False
    if "confirmed_rir" not in st.session_state:
        st.session_state["confirmed_rir"] = False
    if "confirmed_empty" not in st.session_state:
        st.session_state["confirmed_empty"] = False
    if "confirmed_peso" not in st.session_state:
        st.session_state["confirmed_peso"] = False
    if "confirmed_reps" not in st.session_state:
        st.session_state["confirmed_reps"] = False
    if "confirmed_combo" not in st.session_state:
        st.session_state["confirmed_combo"] = False
    if "confirmed_rango" not in st.session_state:
        st.session_state["confirmed_rango"] = False

    # === Validación Rango ===
    # Limpiar rangos
    df['Rango'] = df['Rango'].apply(clean_rango)
    invalid_rango = df[~df['Rango'].apply(is_valid_rango)]
    if not invalid_rango.empty:
        st.warning("Hay técnicas no válidas en la columna 'Rango'. Corregirlas por favor.")
        st.dataframe(invalid_rango[["Ejercicio", "Rango"]])
    else:
        st.session_state["confirmed_rango"] = True
    # === Validación RIR ===
    valid_rirs = {"f","F", "0", "1", "2", "3", "4", "5", 0, 1, 2, 3, 4, 5}
    df['RIR'] = df['RIR'].apply(lambda x: str(int(x)) if x != "F" or "f" else x)
    invalid_rir = df[(df[numeric_cols].sum(axis=1) != 0) & (~df["RIR"].astype(str).isin(valid_rirs))]
    if not invalid_rir.empty:
        st.warning("Hay valores no válidos en RIR. Solo se permite: F, 0 a 5.")
        st.dataframe(invalid_rir[["Ejercicio", "RIR"]])
    else:
        st.session_state["confirmed_rir"] = True

    # === Validación sets vacíos ===
    empty_sets = df[df[numeric_cols].sum(axis=1) == 0]
    empty_ratio = len(empty_sets) / len(df)
    if empty_ratio > 0.5:
        st.warning(f"¿Es un error o no te dió tiempo de entrenar? El {empty_ratio * 100:.0f}% de tus sets están vacíos")
        st.session_state["confirmed_empty"] = st.checkbox("Confirmo que los sets vacíos son intencionales", key="check_empty")
    else:
        st.session_state["confirmed_empty"] = True

    # === Validación pesos altos ===
    pesos_altos = df[df["Peso"] >= 300]
    if not pesos_altos.empty:
        st.warning("Verifica si estos pesos son correctos. Si lo son, pasa link de tu creatina.")
        st.dataframe(pesos_altos[["Ejercicio", "Peso"]])
        st.session_state["confirmed_peso"] = st.checkbox("Confirmo que los pesos son correctos", key="check_peso")
    else:
        st.session_state["confirmed_peso"] = True

    # === Validación reps altas ===
    reps_altas = df[df["Reps"] >= 50]
    if not reps_altas.empty:
        st.warning("Verifica si esto es un error...o si tienes mucho tiempo libre ")
        st.dataframe(reps_altas[["Ejercicio", "Reps"]])
        st.session_state["confirmed_reps"] = st.checkbox("Confirmo que las reps son correctas", key="check_reps")
    else:
        st.session_state["confirmed_reps"] = True

    # === Validación combinaciones raras reps/peso ===
    combo = df[((df["Reps"] == 0) & (df["Peso"] != 0)) | ((df["Reps"] != 0) & (df["Peso"] == 0))]
    if not combo.empty:
        st.warning("¿Estas series fantasmas son correctas?")
        st.dataframe(combo[["Ejercicio", "Reps", "Peso"]])
        st.session_state["confirmed_combo"] = st.checkbox("Confirmo que estas combinaciones son correctas", key="check_combo")
    else:
        st.session_state["confirmed_combo"] = True

    # === Confirmación global ===
    checks = [
        st.session_state["confirmed_rir"],
        st.session_state["confirmed_empty"],
        st.session_state["confirmed_peso"],
        st.session_state["confirmed_reps"],
        st.session_state["confirmed_combo"],
        st.session_state["confirmed_rango"]
    ]

    if not all(checks):
        st.info("Aún quedan advertencias sin confirmar. Por favor revísalas antes de continuar.")
        return None

    # /////// Limpieza final
    df.replace([np.inf, -np.inf, None], np.nan, inplace=True)
    df['RIR'] = df['RIR'].replace({'f': 'F'}).astype(str)
    # Tratar nulos
    df[numeric_cols] = df[numeric_cols].fillna(0)
    df['Ejercicio'] = df['Ejercicio'].ffill()
    df['Rango'] = df['Rango'].fillna('')
    # Redondear a múltiplos de 0.25 los pesos usados
    df['Peso'] = df['Peso'].apply(lambda x: round(x * 4) / 4 if x != 0 else 0)

    return df

