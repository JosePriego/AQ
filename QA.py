import streamlit as st
import pandas as pd
from difflib import get_close_matches

st.set_page_config(page_title="Gestor Bibliotecario MARC21", layout="wide")

@st.cache_data
def cargar_datos():
    try:
        # Cargamos el archivo Excel
        df = pd.read_excel("biblioteca.xlsx", dtype=str)
        df.columns = [str(c).strip() for c in df.columns]
        return df
    except Exception as e:
        st.error(f"Error al cargar la base de datos: {e}")
        return None

def extraer_entidad(pregunta):
    """Limpia la pregunta para extraer el nombre/título"""
    ruido = ["QUÉ", "QUE", "QUIÉN", "QUIEN", "DÓNDE", "DONDE", "CUÁNDO", "CUANDO", 
             "CÓMO", "COMO", "CUÁNTO", "CUANTO", "ISBN", "ESCRIBIÓ", "ESCRIBIO", "DE", "EL", "LA"]
    palabras = pregunta.replace("?", "").replace("¿", "").split()
    return " ".join([p for p in palabras if p.upper() not in ruido]).strip()

def mostrar_ficha_marc(df_resultados):
    """Muestra los registros uno a uno en formato vertical"""
    if 'indice_registro' not in st.session_state:
        st.session_state.indice_registro = 0
    
    total = len(df_resultados)
    if total > 1:
        c1, c2, c3 = st.columns([1, 2, 1])
        if c1.button("⬅️ Anterior"):
            st.session_state.indice_registro = max(0, st.session_state.indice_registro - 1)
        c2.write(f"Registro {st.session_state.indice_registro + 1} de {total}")
        if c3.button("Siguiente ➡️"):
            st.session_state.indice_registro = min(total - 1, st.session_state.indice_registro + 1)
    
    reg = df_resultados.iloc[[st.session_state.indice_registro]].copy()
    
    # Lógica de Anónimo en el campo 100
    if "100" in reg.columns:
        if pd.isna(reg.iloc[0]["100"]) or str(reg.iloc[0]["100"]).strip().lower() in ["nan", ""]:
            reg["100"] = "Anónimo"

    ficha = reg.T
    ficha.columns = ["Contenido"]
    st.table(ficha)

# --- APLICACIÓN ---
st.title("📚 Sistema de Recuperación MARC-21")
df = cargar_datos()

if df is not None:
    # 1. Cajón de opciones (Sidebar)
    with st.sidebar:
        st.header("Opciones de búsqueda")
        modo = st.radio("Selecciona el buscador:", ["General (Taxonomía)", "Materias (Etiqueta 650)"])
        st.divider()
        st.caption("Usa el modo General para preguntas como '¿Quién escribió...?' o '¿Qué escribió...?'.")
        st.caption("Usa el modo Materias para términos directos como 'Psicología' o 'Derecho'.")

    # 2. Entrada de texto dinámica
    placeholder = "Escribe tu pregunta..." if modo == "General (Taxonomía)" else "[Poner solo la materia a recuperar]"
    user_input = st.text_input(placeholder)

    if user_input:
        # Reset de navegación para nuevas búsquedas
        if 'ultima_q' not in st.session_state or st.session_state.ultima_q != user_input:
            st.session_state.indice_registro = 0
            st.session_state.ultima_q = user_input

        if modo == "Materias (Etiqueta 650)":
            col_busq, col_res = "650", "245"
            entidad = user_input.strip()
            modo_info = "Búsqueda por Materia"
        else:
            # Lógica de Taxonomía General
            p_up = user_input.upper()
            entidad = extraer_entidad(user_input)
            if "ISBN" in p_up: col_busq, col_res = "20", "245"
            elif any(w in p_up for w in ["QUIÉN", "QUIEN"]): col_busq, col_res = "245", "100"
            elif any(w in p_up for w in ["QUÉ", "QUE"]): col_busq, col_res = "100", "245"
            elif any(w in p_up for w in ["DÓNDE", "CUÁNDO", "DONDE", "CUANDO"]): col_busq, col_res = "245", "260"
            elif any(w in p_up for w in ["CÓMO", "CUÁNTO", "COMO", "CUANTO"]): col_busq, col_res = "245", "300"
            else: col_busq, col_res = "245", "100"
            modo_info = "General"

        # 3. Ejecución de la búsqueda
        if col_busq in df.columns:
            mask = df[col_busq].str.contains(entidad, case=False, na=False)
            resultados = df[mask]

            if not resultados.empty:
                st.info(f"**Modo:** {modo_info} | **Buscando:** {entidad}")
                
                ver_marc = st.checkbox("🔍 Visualizar Ficha MARC21 completa")
                
                if ver_marc:
                    mostrar_ficha_marc(resultados)
                else:
                    # Vista rápida de resultados
                    for r in resultados[col_res].unique():
                        # Control de Anónimos en vista rápida
                        if (pd.isna(r) or str(r).lower() == "nan") and col_res == "100":
                            st.success("✅ Autor: Anónimo")
                        else:
                            st.success(f"✅ {r}")
            else:
                # 4. Sugerencias si no hay resultados
                st.warning(f"No se encontró nada para '{entidad}'.")
                posibles = df[col_busq].dropna().unique().tolist()
                sug = get_close_matches(entidad, posibles, n=3, cutoff=0.4)
                
                if sug:
                    st.write("¿Quizás buscabas una de estas materias/títulos?")
                    cols = st.columns(len(sug))
                    for i, s in enumerate(sug):
                        if cols[i].button(s):
                            mostrar_ficha_marc(df[df[col_busq] == s])
                else:
                    st.error("No hay registros ni sugerencias cercanas.")
        else:
            st.error(f"La etiqueta MARC {col_busq} no existe en el Excel.")
