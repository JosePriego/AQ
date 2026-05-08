import streamlit as st
import pandas as pd
from difflib import get_close_matches

@st.cache_data
def cargar_datos():
    try:
        df = pd.read_excel("biblioteca.xlsx", dtype=str)
        df.columns = [str(c).strip() for c in df.columns]
        return df
    except Exception as e:
        st.error(f"Error al cargar Excel: {e}")
        return None

def extraer_entidad(pregunta):
    ruido = ["QUÉ", "QUE", "QUIÉN", "QUIEN", "DÓNDE", "DONDE", "ESCRIBIÓ", "ESCRIBIO", "DE", "EL", "LA"]
    palabras = pregunta.replace("?", "").replace("¿", "").split()
    limpio = [p for p in palabras if p.upper() not in ruido]
    return " ".join(limpio).strip()

# --- UI ---
st.title("📚 Asistente Inteligente MARC-21")
df = cargar_datos()

if df is not None:
    pregunta_usuario = st.text_input("¿Qué buscas hoy?")

    if pregunta_usuario:
        entidad = extraer_entidad(pregunta_usuario)
        
        if entidad:
            pregunta_up = pregunta_usuario.upper()
            
            # Definir lógica de columnas según taxonomía
            if "QUIÉN" in pregunta_up or "QUIEN" in pregunta_up:
                col_busqueda, col_res = "245", "100"
            elif "QUÉ" in pregunta_up or "QUE" in pregunta_up:
                col_busqueda, col_res = "100", "245"
            else:
                col_busqueda, col_res = "245", "260"

            # 1. Intento de búsqueda normal (insensible a mayúsculas)
            mask = df[col_busqueda].str.contains(entidad, case=False, na=False)
            resultados = df[mask]

            if not resultados.empty:
                for res in resultados[col_res].unique():
                    st.success(f"✅ Encontrado: {res}")
            
            # 2. SI NO HAY RESULTADOS: Modo Sugerencia
            else:
                st.info(f"No encontré '{entidad}' exactamente...")
                
                # Obtenemos todos los valores únicos de la columna de búsqueda
                posibilidades = df[col_busqueda].dropna().unique().tolist()
                
                # Buscamos las 3 mejores coincidencias (punto de corte 0.6 de similitud)
                sugerencias = get_close_matches(entidad, posibilidades, n=3, cutoff=0.6)
                
                if sugerencias:
                    st.warning(f"¿Quizás quisiste decir uno de estos?")
                    for s in sugerencias:
                        # Botón para que el usuario pueda hacer clic en la sugerencia
                        if st.button(f"🔍 {s}"):
                            # Si pulsa el botón, filtramos por esa sugerencia
                            match_sugerencia = df[df[col_busqueda] == s]
                            for r in match_sugerencia[col_res].unique():
                                st.success(f"Resultado para {s}: {r}")
                else:
                    st.error("No se encontraron coincidencias ni sugerencias cercanas.")
