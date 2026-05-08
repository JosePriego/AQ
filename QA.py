import streamlit as st
import pandas as pd
import re
from difflib import get_close_matches

# 1. Configuración de la página
st.set_page_config(page_title="Sistema Bibliotecario MARC21", layout="wide", page_icon="📚")

# 2. Carga de datos
@st.cache_data
def cargar_datos():
    try:
        df = pd.read_excel("biblioteca.xlsx", dtype=str)
        df.columns = [str(c).strip() for c in df.columns]
        return df
    except Exception as e:
        st.error(f"Error crítico: No se pudo cargar 'biblioteca.xlsx'. {e}")
        return None

# 3. Funciones de apoyo
def extraer_entidad(pregunta):
    ruido = ["QUÉ", "QUE", "QUIÉN", "QUIEN", "DÓNDE", "DONDE", "CUÁNDO", "CUANDO", 
             "CÓMO", "COMO", "CUÁNTO", "CUANTO", "ISBN", "ESCRIBIÓ", "ESCRIBIO", "DE", "EL", "LA"]
    palabras = pregunta.replace("?", "").replace("¿", "").split()
    return " ".join([p for p in palabras if p.upper() not in ruido]).strip()

def ejecutar_busqueda_exacta(df, columna, termino):
    termino_esc = re.escape(termino)
    patron = rf"\b{termino_esc}\b"
    try:
        mask = df[columna].str.contains(patron, case=False, na=False, regex=True)
        return df[mask]
    except:
        return df[df[columna].str.contains(termino, case=False, na=False)]

def mostrar_ficha_marc():
    resultados = st.session_state.resultados_actuales
    total = len(resultados)
    
    if total > 0:
        st.divider()
        if total > 1:
            c1, c2, c3 = st.columns([1, 2, 1])
            if c1.button("⬅️ Anterior"):
                st.session_state.indice_registro = max(0, st.session_state.indice_registro - 1)
            
            c2.markdown(f"<h3 style='text-align: center;'>Registro {st.session_state.indice_registro + 1} de {total}</h3>", unsafe_allow_html=True)
            
            if c3.button("Siguiente ➡️"):
                st.session_state.indice_registro = min(total - 1, st.session_state.indice_registro + 1)
        
        reg = resultados.iloc[[st.session_state.indice_registro]].copy()
        
        if "100" in reg.columns:
            val = reg.iloc[0]["100"]
            if pd.isna(val) or str(val).strip().lower() in ["nan", ""]:
                reg["100"] = "Anónimo"

        ficha = reg.T
        ficha.columns = ["Información Bibliográfica"]
        ficha.index.name = "Etiqueta MARC"
        
        st.table(ficha)

# --- NUEVA FUNCIÓN CALLBACK PARA LAS SUGERENCIAS ---
def aplicar_sugerencia(sugerencia, columna, dataframe):
    """Actualiza el estado de la aplicación antes de que se recargue la página"""
    st.session_state.resultados_actuales = dataframe[dataframe[columna] == sugerencia]
    st.session_state.indice_registro = 0

# --- INICIALIZACIÓN DE VARIABLES DE ESTADO ---
if 'indice_registro' not in st.session_state: st.session_state.indice_registro = 0
if 'resultados_actuales' not in st.session_state: st.session_state.resultados_actuales = pd.DataFrame()
if 'ultima_q' not in st.session_state: st.session_state.ultima_q = ""
if 'col_respuesta_rapida' not in st.session_state: st.session_state.col_respuesta_rapida = "245"

# --- CUERPO DE LA APLICACIÓN ---
st.title("📚 Sistema de Recuperación de Información")
st.markdown("Basado en aproximación teórica de preguntas-respuestas y formato MARC21.")

df = cargar_datos()

if df is not None:
    with st.sidebar:
        st.header("Configuración")
        modo = st.radio("Selecciona el motor de búsqueda:", 
                        ["General (Taxonomía)", "Materias (Etiqueta 650)"])
        st.divider()
        st.info("💡 **Consejo:** En el modo materias, escribe el concepto directo (ej. Historia). En modo General, puedes preguntar '¿Quién escribió...?'")

    placeholder = "¿Quién escribió...?" if modo == "General (Taxonomía)" else "[Poner solo la materia a recuperar]"
    user_input = st.text_input("Buscador:", placeholder=placeholder)

    if user_input:
        if st.session_state.ultima_q != user_input:
            st.session_state.indice_registro = 0
            st.session_state.ultima_q = user_input
            
            if modo == "Materias (Etiqueta 650)":
                col_busq, col_res = "650", "245"
                entidad = user_input.strip()
            else:
                p_up = user_input.upper()
                entidad = extraer_entidad(user_input)
                
                if "ISBN" in p_up: col_busq, col_res = "20", "245"
                elif any(w in p_up for w in ["QUIÉN", "QUIEN"]): col_busq, col_res = "245", "100"
                elif any(w in p_up for w in ["QUÉ", "QUE"]): col_busq, col_res = "100", "245"
                elif any(w in p_up for w in ["DÓNDE", "DONDE", "CUÁNDO", "CUANDO"]): col_busq, col_res = "245", "260"
                elif any(w in p_up for w in ["CÓMO", "COMO", "CUÁNTO", "CUANTO"]): col_busq, col_res = "245", "300"
                else: col_busq, col_res = "245", "100"

            st.session_state.resultados_actuales = ejecutar_busqueda_exacta(df, col_busq, entidad)
            st.session_state.col_respuesta_rapida = col_res

        # --- MOSTRAR RESULTADOS ---
        resultados = st.session_state.resultados_actuales
        
        if not resultados.empty:
            st.write(f"Se han encontrado **{len(resultados)}** coincidencias.")
            
            ver_marc = st.checkbox("🔍 Visualizar Ficha Técnica MARC21 (Modo vertical)")
            
            if ver_marc:
                mostrar_ficha_marc()
            else:
                col_mostrar = st.session_state.col_respuesta_rapida
                for r in resultados[col_mostrar].unique():
                    if (pd.isna(r) or str(r).lower() == "nan") and col_mostrar == "100":
                        st.success("✅ Autor: Anónimo")
                    else:
                        st.success(f"✅ {r}")
        else:
            st.warning(f"No se encontró el término exacto.")
            
            if modo == "Materias (Etiqueta 650)": c_sug = "650"
            else: c_sug = "245"
            
            posibles = df[c_sug].dropna().unique().tolist()
            sug = get_close_matches(user_input, posibles, n=3, cutoff=0.4)
            
            if sug:
                st.info("¿Quizás buscabas algo de esto?")
                cols = st.columns(len(sug))
                for i, s in enumerate(sug):
                    # AQUÍ ESTÁ LA MAGIA: Usamos on_click para llamar a la función sin usar st.rerun()
                    cols[i].button(s, on_click=aplicar_sugerencia, args=(s, c_sug, df))
            else:
                st.error("No hay registros ni sugerencias similares en la base de datos.")
else:
    st.info("Esperando el archivo 'biblioteca.xlsx' para comenzar...")
