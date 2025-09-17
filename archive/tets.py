import streamlit as st
import pandas as pd
import numpy as np
import re

# Técnicas válidas
eh_techniques = ['Myo-reps', 'Parciales', 'Dropset', 'Rest-pause', 'Clúster']

def clean_rango(value):
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
    if pd.isna(val) or val == "":
        return True

    val_str = str(val).strip()

    # Número suelto
    try:
        float(val_str)
        return True
    except ValueError:
        pass

    # Detectar 2 números => lo consideramos un rango
    nums = re.findall(r"\d+(?:\.\d+)?", val_str)
    if len(nums) == 2:
        return True

    return val_str.lower().title() in eh_techniques

# ==== Datos de prueba ====
data = {
    "Ejercicio": ["Curl", "Extensión", "Press", "Remo", "Vuelos", "Sentadilla"],
    "Rango": ["8-9", "8 -9", "8- 9", "8 - 9", "dropset", "RandomTexto"]
}
df = pd.DataFrame(data)

st.title("Test de limpieza y validación de columna 'Rango'")
st.subheader("🔍 Antes de limpiar")
st.dataframe(df)

# Limpieza
df['Rango'] = df['Rango'].apply(clean_rango)

st.subheader("🧼 Después de limpiar")
st.dataframe(df)

# Validación
invalid_rows = df[~df['Rango'].apply(is_valid_rango)]

if not invalid_rows.empty:
    st.warning("⚠️ Hay valores no válidos en la columna 'Rango':")
    st.dataframe(invalid_rows)
else:
    st.success("✅ Todos los valores de 'Rango' son válidos.")
