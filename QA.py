import streamlit as st
import pandas as pd

# 1. Diccionario de mapeo basado en tu taxonomía
MAPEO_MARC = {
    "QUIÉN": {"busca_en": ["245"], "devuelve": ["100", "110", "111"]}, # Pregunta por autor, busca por título
    "QUÉ": {"busca_en": ["100", "110", "700"], "devuelve": ["245"]},   # Pregunta por obra, busca por autor
    "DÓNDE": {"busca_en": ["245"], "devuelve": ["260"]},             # Pregunta lugar, busca por título
}

@st.cache_data
def cargar_datos():
    # Asegúrate de que el nombre del archivo coincida
    # df = pd.read_excel("tu_archivo.xlsx", dtype=str) 
    data = {
        "100": ["Waldron, Jeremy", "Cervantes, Miguel de"],
        "245": ["Law and Disagreement", "Don Quijote de la Mancha"],
        "260": ["Oxford, 1999", "Madrid, 1605"]
    }
    return pd.DataFrame(data)

def extraer_entidad(pregunta):
    # Eliminamos las partículas interrogativas para quedarnos con el nombre/título
    particulas = ["QUÉ", "QUE", "QUIÉN", "QUIEN", "DÓNDE", "DONDE", "ESCRIBIÓ", "ESCRIBIO"]
    limpio = pregunta.upper().replace("?", "").replace("¿", "")
    for p in particulas:
        limpio = limpio.replace(p, "")
    return limpio.strip()

st.title("📚 Sistema de Recuperación MARC-21")

df = cargar_datos()
pregunta_usuario = st.text_input("Haz tu pregunta:")

if pregunta_usuario:
    # Identificar Clase
    pregunta_up = pregunta_usuario.upper()
    clase = None
    if "QUIÉN" in pregunta_up or "QUIEN" in pregunta_up: clase = "QUIÉN"
    elif "QUÉ" in pregunta_up or "QUE" in pregunta_up: clase = "QUÉ"
    elif "DÓNDE" in pregunta_up or "DONDE" in pregunta_up: clase = "DÓNDE"

    if clase:
        entidad = extraer_entidad(pregunta_usuario)
        st.info(f"Buscando información sobre: **{entidad}**")
        
        # Lógica de búsqueda:
        # Buscamos la 'entidad' en las columnas que definimos en MAPEO_MARC
        columnas_busqueda = MAPEO_MARC[clase]["busca_en"]
        columnas_respuesta = MAPEO_MARC[clase]["devuelve"]
        
        resultado = pd.DataFrame()
        for col in columnas_busqueda:
            if col in df.columns:
                match = df[df[col].str.contains(entidad, case=False, na=False)]
                resultado = pd.concat([resultado, match])

        if not resultado.empty:
            for _, fila in resultado.iterrows():
                for c_res in columnas_respuesta:
                    st.success(f"Encontrado: **{fila[c_res]}**")
        else:
            st.warning(f"No encontré registros para '{entidad}' en los campos de {clase}.")
    else:
        st.error("Por favor, formula una pregunta que empiece por Qué, Quién o Dónde.")
