import streamlit as st
import pandas as pd
from difflib import get_close_matches

st.set_page_config(page_title="Gestor Bibliotecario MARC21", layout="wide")

@st.cache_data
def cargar_datos():
    try:
        df = pd.read_excel("biblioteca.xlsx", dtype=str)
        df.columns = [str(c).strip() for c in df.columns]
        return df
    except Exception as e:
        st.error(f"Error al cargar la base de datos: {e}")
        return None

def extraer_entidad(pregunta):
    ruido = ["QUÉ", "QUE", "QUIÉN", "QUIEN", "DÓNDE", "DONDE", "CUÁNDO", "CUANDO", 
             "CÓMO", "COMO", "CUÁNTO", "CUANTO", "ISBN", "ESCRIBIÓ", "ESCRIBIO", "DE", "EL", "LA"]
    palabras = pregunta.replace("?", "").replace("¿", "").split()
    return " ".join([p for p in palabras if p.upper() not in ruido]).strip()

def mostrar_ficha_marc():
    """Muestra los registros guardados en el estado de sesión"""
    # Recuperamos los resultados guardados
    resultados = st.session_state.resultados_actuales
    total = len(resultados)
    
    if total > 0:
        if total > 1:
            c1, c2, c3 = st.columns([1, 2, 1])
            # Botón Anterior
            if c1.button("⬅️ Anterior"):
                if st.session_state.indice_registro > 0:
                    st.session_state.indice_registro -= 1
            
            c2.write(f"Registro {st.session_state.indice_registro + 1} de {total}")
            
            # Botón Siguiente
            if c3.button("Siguiente ➡️"):
                if st.session_state.indice_registro < total - 1:
                    st.session_state.indice_registro += 1
        
        # Extraemos el registro según el índice actual
        reg = resultados.iloc[[st.session_state.indice_registro]].copy()
        
        # Lógica de Anónimo
        if "100" in reg.columns:
            val = reg.iloc[0]["100"]
            if pd.isna(val) or str(val).strip().lower() in ["nan", ""]:
                reg["100"] = "Anónimo"

        ficha = reg.T
        ficha.columns = ["Contenido"]
        st.table(ficha)

# --- INICIALIZACIÓN DE ESTADOS ---
if 'indice_registro' not in st.session_state: st.session_state.indice_registro = 0
if 'resultados_actuales' not in st.session_state: st.session_state.resultados_actuales = pd.DataFrame()
if 'ultima_q' not in st.session_state: st.session_state.ultima_q = ""

# --- APLICACIÓN ---
st.title("📚 Sistema de Recuperación MARC-21")
df = cargar_datos()

if df is not None:
    with st.sidebar:
        st.header("Opciones")
        modo = st.radio("Buscador:", ["General (Taxonomía)", "Materias (Etiqueta 650)"])

    placeholder = "Escribe tu pregunta..." if modo == "General (Taxonomía)" else "Materia a recuperar..."
    user_input = st.text_input(placeholder)

    if user_input:
        # Si la pregunta cambia, reseteamos todo
        if st.session_state.ultima_q != user_input:
            st.session_state.indice_registro = 0
            st.session_state.ultima_q = user_input
            
            # Realizamos la búsqueda y la guardamos en el estado
            if modo == "Materias (Etiqueta 650)":
                col_busq = "650"
                entidad = user_input.strip()
            else:
                entidad = extraer_entidad(user_input)
                p_up = user_input.upper()
                if "ISBN" in p_up: col_busq = "20"
                elif any(w in p_up for w in ["QUIÉN", "QUIEN"]): col_busq = "245"
                elif any(w in p_up for w in ["QUÉ", "QUE"]): col_busq = "100"
                else: col_busq = "245"

            mask = df[col_busq].str.contains(entidad, case=False, na=False)
            st.session_state.resultados_actuales = df[mask]

        # --- MOSTRAR RESULTADOS DESDE EL ESTADO ---
        if not st.session_state.resultados_actuales.empty:
            ver_marc = st.checkbox("🔍 Visualizar Ficha MARC21 completa")
            
            if ver_marc:
                mostrar_ficha_marc()
            else:
                # Vista rápida (usamos la columna de respuesta lógica según el modo)
                # (Aquí puedes añadir la lógica de qué columna mostrar en vista rápida)
                st.write(f"Se han encontrado {len(st.session_state.resultados_actuales)} coincidencias.")
                for r in st.session_state.resultados_actuales.iloc[:, 2].unique(): # Muestra títulos por defecto
                    st.success(f"✅ {r}")
        else:
            st.error("No se encontraron resultados.")
