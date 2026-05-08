import streamlit as st
import pandas as pd
from difflib import get_close_matches

st.set_page_config(page_title="Visualizador MARC21 Pro", layout="wide")

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
    return " ".join([p for p in palabras if p.upper() not in ruido]).strip()

# --- FUNCIÓN PARA LA FICHA MARC21 ---
def mostrar_ficha_marc(df_resultados):
    # Usamos session_state para navegar entre resultados si hay varios
    if 'indice_registro' not in st.session_state:
        st.session_state.indice_registro = 0

    # Si hay más de un resultado, mostramos controles de navegación
    total = len(df_resultados)
    if total > 1:
        col1, col2, col3 = st.columns([1, 2, 1])
        if col1.button("⬅️ Anterior") and st.session_state.indice_registro > 0:
            st.session_state.indice_registro -= 1
        col2.write(f"Registro {st.session_state.indice_registro + 1} de {total}")
        if col3.button("Siguiente ➡️") and st.session_state.indice_registro < total - 1:
            st.session_state.indice_registro += 1
    
    # Seleccionamos el registro actual
    registro_actual = df_resultados.iloc[[st.session_state.indice_registro]]
    
    # TRANSPOSICIÓN: Convertimos columnas en filas
    ficha = registro_actual.T
    ficha.columns = ["Información del Registro"]
    ficha.index.name = "Etiqueta MARC"

    # Reemplazamos valores vacíos por "Anónimo" o "No disponible"
    if "100" in ficha.index:
        val_100 = ficha.loc["100", "Información del Registro"]
        if pd.isna(val_100) or str(val_100).strip().lower() in ["nan", ""]:
            ficha.loc["100", "Información del Registro"] = "Anónimo"

    st.table(ficha) # st.table se ve más estático y profesional para fichas

# --- INTERFAZ PRINCIPAL ---
st.title("📚 Sistema de Recuperación e Intérprete MARC-21")
df = cargar_datos()

if df is not None:
    pregunta_usuario = st.text_input("Haz tu consulta:")

    if pregunta_usuario:
        entidad = extraer_entidad(pregunta_usuario)
        pregunta_up = pregunta_usuario.upper()
        
        # Resetear el índice de navegación al hacer una nueva búsqueda
        st.session_state.indice_registro = 0

        # Lógica de campos
        if any(w in pregunta_up for w in ["QUIÉN", "QUIEN"]):
            col_busqueda, col_res = "245", "100"
        elif any(w in pregunta_up for w in ["QUÉ", "QUE"]):
            col_busqueda, col_res = "100", "245"
        else:
            col_busqueda, col_res = "245", "260"

        # Búsqueda
        mask = df[col_busqueda].str.contains(entidad, case=False, na=False)
        resultados = df[mask]

        if not resultados.empty:
            st.subheader(f"Resultados para: {entidad}")
            
            # Botón para activar la vista MARC
            ver_marc = st.checkbox("🔍 Ver detalles en formato Ficha MARC21")
            
            if ver_marc:
                mostrar_ficha_marc(resultados)
            else:
                # Vista rápida
                for res in resultados[col_res].unique():
                    final = "Anónimo" if (pd.isna(res) or str(res).lower()=="nan") and col_res=="100" else res
                    st.success(f"✅ {final}")
        
        else:
            # Sugerencias
            posibilidades = df[col_busqueda].dropna().unique().tolist()
            sugerencias = get_close_matches(entidad, posibilidades, n=3, cutoff=0.4)
            if sugerencias:
                st.info("No hay coincidencia exacta. ¿Quizás quisiste decir...?")
                cols = st.columns(len(sugerencias))
                for i, sug in enumerate(sugerencias):
                    if cols[i].button(sug):
                        res_sug = df[df[col_busqueda] == sug]
                        mostrar_ficha_marc(res_sug)
            else:
                st.error("No se encontraron registros.")
