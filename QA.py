import streamlit as st
import pandas as pd
import re
from difflib import get_close_matches
import os

# 1. Configuración de la página
st.set_page_config(page_title="SIGB MARC21", layout="wide", page_icon="📚")

# 2. Carga de datos (Con gestión de caché)
@st.cache_data
def cargar_datos():
    try:
        if not os.path.exists("biblioteca.xlsx"):
            # Si el archivo no existe, creamos uno básico vacío para empezar
            df_vacio = pd.DataFrame(columns=["20", "100", "245", "260", "300", "650"])
            df_vacio.to_excel("biblioteca.xlsx", index=False)
            return df_vacio
            
        df = pd.read_excel("biblioteca.xlsx", dtype=str)
        df.columns = [str(c).strip() for c in df.columns]
        return df
    except Exception as e:
        st.error(f"Error crítico al cargar 'biblioteca.xlsx': {e}")
        return None

# 3. Funciones del Buscador (OPAC)
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

def aplicar_sugerencia(sugerencia, columna, dataframe):
    st.session_state.resultados_actuales = dataframe[dataframe[columna] == sugerencia]
    st.session_state.indice_registro = 0

# --- INICIALIZACIÓN DE VARIABLES ---
if 'indice_registro' not in st.session_state: st.session_state.indice_registro = 0
if 'resultados_actuales' not in st.session_state: st.session_state.resultados_actuales = pd.DataFrame()
if 'ultima_q' not in st.session_state: st.session_state.ultima_q = ""
if 'col_respuesta_rapida' not in st.session_state: st.session_state.col_respuesta_rapida = "245"

df = cargar_datos()

# --- NAVEGACIÓN PRINCIPAL ---
st.sidebar.title("🏛️ Biblioteca Principal")
modo_app = st.sidebar.radio("Navegación:", ["🔍 OPAC (Buscador Público)", "✍️ Módulo de Catalogación"])
st.sidebar.divider()

# ==========================================
# PÁGINA 1: OPAC (Buscador)
# ==========================================
if modo_app == "🔍 OPAC (Buscador Público)":
    st.title("📚 Catálogo de Acceso Público (OPAC)")
    st.markdown("Consulta nuestros fondos mediante preguntas naturales o búsqueda por materias.")

    if df is not None:
        modo_busqueda = st.radio("Filtro de búsqueda:", ["General (Taxonomía)", "Materias (Etiqueta 650)"], horizontal=True)

        placeholder = "¿Quién escribió...?" if modo_busqueda == "General (Taxonomía)" else "[Poner solo la materia]"
        user_input = st.text_input("Buscador:", placeholder=placeholder)

        if user_input:
            if st.session_state.ultima_q != user_input:
                st.session_state.indice_registro = 0
                st.session_state.ultima_q = user_input
                
                if modo_busqueda == "Materias (Etiqueta 650)":
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

            resultados = st.session_state.resultados_actuales
            
            if not resultados.empty:
                st.write(f"Se han encontrado **{len(resultados)}** coincidencias.")
                ver_marc = st.checkbox("🔍 Visualizar Ficha Técnica MARC21")
                
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
                st.warning("No se encontró el término exacto.")
                c_sug = "650" if modo_busqueda == "Materias (Etiqueta 650)" else "245"
                
                posibles = df[c_sug].dropna().unique().tolist()
                sug = get_close_matches(user_input, posibles, n=3, cutoff=0.4)
                
                if sug:
                    st.info("¿Quizás buscabas algo de esto?")
                    cols = st.columns(len(sug))
                    for i, s in enumerate(sug):
                        cols[i].button(s, on_click=aplicar_sugerencia, args=(s, c_sug, df))
                else:
                    st.error("No hay registros ni sugerencias similares en la base de datos.")

# ==========================================
# PÁGINA 2: MÓDULO DE CATALOGACIÓN
# ==========================================
elif modo_app == "✍️ Módulo de Catalogación":
    st.title("✍️ Herramienta de Catalogación MARC21")
    st.markdown("Introduce los datos del nuevo ejemplar. Los campos vacíos se guardarán como nulos para permitir registros parciales o anónimos.")

    # Utilizamos st.form para que la página no se recargue con cada letra que escribes
    with st.form("formulario_catalogacion", clear_on_submit=True):
        st.subheader("Datos del Registro")
        
        col1, col2 = st.columns(2)
        with col1:
            nuevo_20 = st.text_input("20 - ISBN", placeholder="Ej: 9788418810763")
            nuevo_100 = st.text_input("100 - Autor Principal", placeholder="Ej: Apellido, Nombre")
            nuevo_245 = st.text_input("245 - Título", placeholder="Título de la obra")
        with col2:
            nuevo_260 = st.text_input("260 - Publicación", placeholder="Ej: Lugar, Fecha")
            nuevo_300 = st.text_input("300 - Descripción Física", placeholder="Ej: 350 p. ; 21 cm")
            nuevo_650 = st.text_input("650 - Materias", placeholder="Ej: Inteligencia artificial")
        
        # Botón de guardado
        guardar_btn = st.form_submit_button("💾 Guardar en el Catálogo")

        if guardar_btn:
            # Validación básica: Al menos debe tener un título
            if not nuevo_245.strip():
                st.error("⚠️ El campo 245 (Título) es obligatorio para crear el registro.")
            else:
                # 1. Crear un nuevo registro como diccionario
                nuevo_registro = {
                    "20": nuevo_20.strip() if nuevo_20 else "",
                    "100": nuevo_100.strip() if nuevo_100 else "",
                    "245": nuevo_245.strip(),
                    "260": nuevo_260.strip() if nuevo_260 else "",
                    "300": nuevo_300.strip() if nuevo_300 else "",
                    "650": nuevo_650.strip() if nuevo_650 else ""
                }
                
                # 2. Añadirlo al DataFrame existente
                df_nuevo = pd.DataFrame([nuevo_registro])
                df_actualizado = pd.concat([df, df_nuevo], ignore_index=True)
                
                # 3. Guardar en el archivo Excel
                try:
                    df_actualizado.to_excel("biblioteca.xlsx", index=False)
                    # 4. Limpiar la caché para que el OPAC vea el nuevo libro inmediatamente
                    st.cache_data.clear()
                    st.success(f"✅ ¡El libro '{nuevo_245}' ha sido catalogado con éxito y ya está disponible en el OPAC!")
                except Exception as e:
                    st.error(f"❌ Error al guardar el archivo: {e}. Asegúrate de que el archivo Excel no esté abierto en otro programa.")
