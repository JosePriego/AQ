import streamlit as st
import pandas as pd
from difflib import get_close_matches

st.set_page_config(page_title="MARC21 Expert System", layout="wide")

@st.cache_data
def cargar_datos():
    try:
        df = pd.read_excel("biblioteca.xlsx", dtype=str)
        df.columns = [str(c).strip() for c in df.columns]
        return df
    except Exception as e:
        st.error(f"Error: {e}")
        return None

def extraer_entidad(pregunta):
    ruido = ["QUÉ", "QUE", "QUIÉN", "QUIEN", "DÓNDE", "DONDE", "CUÁNDO", "CUANDO", 
             "CÓMO", "COMO", "CUÁNTO", "CUANTO", "ISBN", "ESCRIBIÓ", "ESCRIBIO", "DE", "EL", "LA"]
    palabras = pregunta.replace("?", "").replace("¿", "").split()
    return " ".join([p for p in palabras if p.upper() not in ruido]).strip()

def mostrar_ficha_marc(df_resultados):
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
    if "100" in reg.columns:
        if pd.isna(reg.iloc[0]["100"]) or str(reg.iloc[0]["100"]).strip().lower() in ["nan", ""]:
            reg["100"] = "Anónimo"
    
    ficha = reg.T
    ficha.columns = ["Contenido del Campo"]
    st.table(ficha)

# --- APP ---
st.title("📚 Recuperación de Información Bibliotecaria Pro")
df = cargar_datos()

if df is not None:
    pregunta_usuario = st.text_input("Escribe tu duda (Quién, Qué, Dónde, ISBN...):")

    if pregunta_usuario:
        entidad = extraer_entidad(pregunta_usuario)
        p_up = pregunta_usuario.upper()
        
        if 'ultima_pregunta' not in st.session_state or st.session_state.ultima_pregunta != pregunta_usuario:
            st.session_state.indice_registro = 0
            st.session_state.ultima_pregunta = pregunta_usuario

        # --- MOTOR DE TAXONOMÍA ---
        if "ISBN" in p_up:
            col_busqueda, col_res = "20", "245"
            modo = "Búsqueda por ISBN"
        elif any(w in p_up for w in ["QUIÉN", "QUIEN"]):
            col_busqueda, col_res = "245", "100"
            modo = "Autoría"
        elif any(w in p_up for w in ["QUÉ", "QUE"]):
            col_busqueda, col_res = "100", "245"
            modo = "Bibliografía"
        elif any(w in p_up for w in ["DÓNDE", "DONDE", "CUÁNDO", "CUANDO"]):
            col_busqueda, col_res = "245", "260"
            modo = "Publicación"
        elif any(w in p_up for w in ["CÓMO", "COMO", "CUÁNTO", "CUANTO"]):
            col_busqueda, col_res = "245", "300"
            modo = "Descripción Física"
        else:
            col_busqueda, col_res = "245", "100"
            modo = "Búsqueda General"

        # Búsqueda (insensible a mayúsculas para texto, exacta para ISBN)
        mask = df[col_busqueda].str.contains(entidad, case=False, na=False)
        resultados = df[mask]

        if not resultados.empty:
            st.info(f"Modo: **{modo}** | Término: *{entidad}*")
            if st.checkbox("🔍 Ver Registro MARC completo"):
                mostrar_ficha_marc(resultados)
            else:
                for res in resultados[col_res].unique():
                    if (pd.isna(res) or str(res).lower()=="nan") and col_res=="100":
                        st.success("✅ Autor: Anónimo")
                    elif pd.isna(res) or str(res).lower()=="nan":
                        st.warning("⚠️ Sin datos en este campo.")
                    else:
                        st.success(f"✅ {res}")
        else:
            # Sugerencias
            posibles = df[col_busqueda].dropna().unique().tolist()
            sug = get_close_matches(entidad, posibles, n=3, cutoff=0.4)
            if sug:
                st.warning("No hay resultados exactos. ¿Buscabas algo de esto?")
                cols = st.columns(len(sug))
                for i, s in enumerate(sug):
                    if cols[i].button(s):
                        mostrar_ficha_marc(df[df[col_busqueda] == s])
            else:
                st.error("No se ha encontrado nada en la base de datos.")
