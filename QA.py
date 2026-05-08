import streamlit as st
import pandas as pd
import re
from difflib import get_close_matches
import os

# 1. Configuración de la página
st.set_page_config(page_title="SIGB MARC21 Pro", layout="wide", page_icon="📚")

# 2. Carga de datos
@st.cache_data
def cargar_datos():
    try:
        if not os.path.exists("biblioteca.xlsx"):
            # Creamos el Excel con la nueva columna 'Material' incluida
            df_vacio = pd.DataFrame(columns=["Material", "20", "100", "245", "260", "300", "650"])
            df_vacio.to_excel("biblioteca.xlsx", index=False)
            return df_vacio
            
        df = pd.read_excel("biblioteca.xlsx", dtype=str)
        df.columns = [str(c).strip() for c in df.columns]
        return df
    except Exception as e:
        st.error(f"Error crítico al cargar 'biblioteca.xlsx': {e}")
        return None

# 3. Funciones del Sistema
def extraer_entidad(pregunta):
    ruido = ["QUÉ", "QUE", "QUIÉN", "QUIEN", "DÓNDE", "DONDE", "CUÁNDO", "CUANDO", 
             "CÓMO", "COMO", "CUÁNTO", "CUANTO", "ISBN", "ESCRIBIÓ", "ESCRIBIO", "DE", "EL", "LA"]
    palabras = pregunta.replace("?", "").replace("¿", "").split()
    return " ".join([p for p in palabras if p.upper() not in ruido]).strip()

def ejecutar_busqueda_exacta(df, columna, termino, filtro_material):
    """Busca por palabra exacta y aplica el filtro de colección"""
    # 1. Filtro de Material (Faceta)
    if filtro_material != "Todos":
        df = df[df["Material"] == filtro_material]

    # 2. Búsqueda Regex
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

# --- FUNCIONES CALLBACK ---
def aplicar_sugerencia(sugerencia, columna, dataframe, filtro_material):
    # Si hay filtro de material, reducimos el dataframe primero
    if filtro_material != "Todos":
        dataframe = dataframe[dataframe["Material"] == filtro_material]
        
    st.session_state.resultados_actuales = dataframe[dataframe[columna] == sugerencia]
    st.session_state.indice_registro = 0

def comprobar_login():
    if st.session_state.password_input == "biblioteca2026":
        st.session_state.autenticado = True
        st.session_state.error_pass = False
    else:
        st.session_state.error_pass = True

def cerrar_sesion():
    st.session_state.autenticado = False

# --- INICIALIZACIÓN DE VARIABLES DE ESTADO ---
if 'indice_registro' not in st.session_state: st.session_state.indice_registro = 0
if 'resultados_actuales' not in st.session_state: st.session_state.resultados_actuales = pd.DataFrame()
if 'ultima_q' not in st.session_state: st.session_state.ultima_q = ""
if 'col_respuesta_rapida' not in st.session_state: st.session_state.col_respuesta_rapida = "245"
if 'autenticado' not in st.session_state: st.session_state.autenticado = False
if 'error_pass' not in st.session_state: st.session_state.error_pass = False

df = cargar_datos()

# --- NAVEGACIÓN PRINCIPAL ---
st.sidebar.title("🏛️ Biblioteca SIGB")
modo_app = st.sidebar.radio("Navegación:", ["🔍 OPAC (Buscador Público)", "✍️ Módulo de Catalogación"])
st.sidebar.divider()

# ==========================================
# PÁGINA 1: OPAC (Buscador)
# ==========================================
if modo_app == "🔍 OPAC (Buscador Público)":
    st.title("📚 Catálogo de Acceso Público (OPAC)")
    
    if df is not None:
        # 1. FACETAS (Material)
        st.write("### 1. Selecciona la colección:")
        filtro_mat = st.radio("Filtro por material:", ["Todos", "Monografías", "Ilustrados", "Cómics"], horizontal=True)
        st.divider()

        # 2. BUSCADOR
        st.write("### 2. ¿Qué deseas buscar?")
        modo_busqueda = st.selectbox("Modo de búsqueda:", ["General (Taxonomía)", "Materias (Etiqueta 650)"])
        
        placeholder = "¿Quién escribió...?" if modo_busqueda == "General (Taxonomía)" else "[Escribe el término exacto]"
        user_input = st.text_input("Buscador:", placeholder=placeholder)

        if user_input:
            if st.session_state.ultima_q != user_input:
                st.session_state.indice_registro = 0
                st.session_state.ultima_q = user_input
                
                # Asignación de columnas según modo
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

                # Búsqueda con filtro de material
                st.session_state.resultados_actuales = ejecutar_busqueda_exacta(df, col_busq, entidad, filtro_mat)
                st.session_state.col_respuesta_rapida = col_res

            resultados = st.session_state.resultados_actuales
            
            # --- MOSTRAR RESULTADOS ---
            if not resultados.empty:
                st.success(f"Se han encontrado **{len(resultados)}** coincidencias en la sección '{filtro_mat}'.")
                ver_marc = st.checkbox("🔍 Visualizar Ficha Técnica MARC21")
                
                if ver_marc:
                    mostrar_ficha_marc()
                else:
                    col_mostrar = st.session_state.col_respuesta_rapida
                    for r in resultados[col_mostrar].unique():
                        if (pd.isna(r) or str(r).lower() == "nan") and col_mostrar == "100":
                            st.write("✅ Autor: Anónimo")
                        else:
                            st.write(f"✅ {r}")
            else:
                st.warning(f"No se encontró el término exacto en la sección '{filtro_mat}'.")
                
                # SUGERENCIAS INTELIGENTES
                c_sug = col_busq
                # Filtramos las posibilidades por el material seleccionado para no sugerir cómics si busca monografías
                if filtro_mat != "Todos":
                    df_filtrado = df[df["Material"] == filtro_mat]
                    posibles = df_filtrado[c_sug].dropna().unique().tolist()
                else:
                    posibles = df[c_sug].dropna().unique().tolist()

                sug = get_close_matches(user_input, posibles, n=3, cutoff=0.4)
                
                if sug:
                    st.info("¿Quizás buscabas algo de esto?")
                    cols = st.columns(len(sug))
                    for i, s in enumerate(sug):
                        cols[i].button(s, on_click=aplicar_sugerencia, args=(s, c_sug, df, filtro_mat))
                else:
                    st.error("No hay registros ni sugerencias similares.")

# ==========================================
# PÁGINA 2: MÓDULO DE CATALOGACIÓN
# ==========================================
elif modo_app == "✍️ Módulo de Catalogación":
    st.title("✍️ Herramienta de Catalogación MARC21")
    
    # PROTECCIÓN POR CONTRASEÑA
    if not st.session_state.autenticado:
        st.info("🔒 Zona restringida al personal. Por favor, identifícate.")
        col_login1, col_login2 = st.columns([1, 2])
        with col_login1:
            st.text_input("Contraseña:", type="password", key="password_input")
            st.button("Entrar", on_click=comprobar_login)
            if st.session_state.error_pass:
                st.error("❌ Contraseña incorrecta.")
    else:
        st.success("🔓 Sesión iniciada correctamente.")
        st.button("Cerrar Sesión", on_click=cerrar_sesion)
        st.divider()

        # FORMULARIO DE CATALOGACIÓN
        with st.form("formulario_catalogacion", clear_on_submit=True):
            st.subheader("Datos del Nuevo Registro")
            
            nuevo_mat = st.selectbox("Colección / Material", ["Monografías", "Ilustrados", "Cómics"])
            
            col1, col2 = st.columns(2)
            with col1:
                nuevo_20 = st.text_input("20 - ISBN")
                nuevo_100 = st.text_input("100 - Autor Principal")
                nuevo_245 = st.text_input("245 - Título")
            with col2:
                nuevo_260 = st.text_input("260 - Publicación")
                nuevo_300 = st.text_input("300 - Descripción Física")
                nuevo_650 = st.text_input("650 - Materias")
            
            guardar_btn = st.form_submit_button("💾 Guardar en el Catálogo")

            if guardar_btn:
                if not nuevo_245.strip():
                    st.error("⚠️ El campo 245 (Título) es obligatorio.")
                else:
                    nuevo_registro = {
                        "Material": nuevo_mat,
                        "20": nuevo_20.strip() if nuevo_20 else "",
                        "100": nuevo_100.strip() if nuevo_100 else "",
                        "245": nuevo_245.strip(),
                        "260": nuevo_260.strip() if nuevo_260 else "",
                        "300": nuevo_300.strip() if nuevo_300 else "",
                        "650": nuevo_650.strip() if nuevo_650 else ""
                    }
                    
                    df_nuevo = pd.DataFrame([nuevo_registro])
                    df_actualizado = pd.concat([df, df_nuevo], ignore_index=True)
                    
                    try:
                        df_actualizado.to_excel("biblioteca.xlsx", index=False)
                        st.cache_data.clear()
                        st.success(f"✅ ¡El libro '{nuevo_245}' ha sido catalogado en '{nuevo_mat}'!")
                    except Exception as e:
                        st.error(f"❌ Error al guardar el archivo: {e}")
