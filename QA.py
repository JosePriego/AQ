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
    if filtro_material != "Todos":
        df = df[df["Material"] == filtro_material]

    termino_esc = re.escape(termino)
    patron = rf"\b{termino_esc}\b"
    try:
        mask = df[columna].str.contains(patron, case=False, na=False, regex=True)
        return df[mask]
    except:
        return df[df[columna].str.contains(termino, case=False, na=False)]

def mostrar_ficha_marc():
    """Muestra el registro con las etiquetas en el orden bibliográfico correcto"""
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
        
        # Seleccionamos el registro
        reg = resultados.iloc[[st.session_state.indice_registro]].copy()
        
        # --- LÓGICA DE ORDENACIÓN DE ETIQUETAS ---
        # Definimos el orden exacto que quieres
        orden_etiquetas = ["Material", "20", "100", "245", "260", "300", "650"]
        
        # Reordenamos las columnas del registro actual según la lista
        # Solo incluimos las que realmente existan en el DataFrame para evitar errores
        columnas_disponibles = [col for col in orden_etiquetas if col in reg.columns]
        # Añadimos al final cualquier otra columna que no esté en la lista (por si añades más en el futuro)
        otras_columnas = [col for col in reg.columns if col not in orden_etiquetas]
        
        reg = reg[columnas_disponibles + otras_columnas]
        # ----------------------------------------

        if "100" in reg.columns:
            val = reg.iloc[0]["100"]
            if pd.isna(val) or str(val).strip().lower() in ["nan", ""]:
                reg["100"] = "Anónimo"

        ficha = reg.T
        ficha.columns = ["Información Bibliográfica"]
        ficha.index.name = "Etiqueta MARC"
        st.table(ficha)

def aplicar_sugerencia(sugerencia, columna, dataframe, filtro_material):
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

# --- ESTADOS ---
if 'indice_registro' not in st.session_state: st.session_state.indice_registro = 0
if 'resultados_actuales' not in st.session_state: st.session_state.resultados_actuales = pd.DataFrame()
if 'ultima_q' not in st.session_state: st.session_state.ultima_q = ""
if 'col_respuesta_rapida' not in st.session_state: st.session_state.col_respuesta_rapida = "245"
if 'autenticado' not in st.session_state: st.session_state.autenticado = False
if 'error_pass' not in st.session_state: st.session_state.error_pass = False

df = cargar_datos()

# --- NAVEGACIÓN ---
st.sidebar.title("🏛️ Biblioteca SIGB")
modo_app = st.sidebar.radio("Navegación:", ["🔍 OPAC (Buscador Público)", "✍️ Módulo de Catalogación"])
st.sidebar.divider()

if modo_app == "🔍 OPAC (Buscador Público)":
    st.title("📚 Catálogo de Acceso Público (OPAC)")
    if df is not None:
        st.write("### 1. Selecciona la colección:")
        filtro_mat = st.radio("Filtro por material:", ["Todos", "Monografías", "Ilustrados", "Cómics"], horizontal=True)
        st.divider()

        st.write("### 2. ¿Qué deseas buscar?")
        # Hemos quitado el modo "Formato (300)" como pediste
        modo_busqueda = st.selectbox("Modo de búsqueda:", ["General (Taxonomía)", "Materias (Etiqueta 650)"])
        
        placeholder = "¿Quién escribió...?" if modo_busqueda == "General (Taxonomía)" else "[Escribe el término exacto]"
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

                st.session_state.resultados_actuales = ejecutar_busqueda_exacta(df, col_busq, entidad, filtro_mat)
                st.session_state.col_respuesta_rapida = col_res

            resultados = st.session_state.resultados_actuales
            
            if not resultados.empty:
                st.success(f"Se han encontrado **{len(resultados)}** coincidencias en '{filtro_mat}'.")
                ver_marc = st.checkbox("🔍 Visualizar Ficha Técnica MARC21")
                if ver_marc:
                    mostrar_ficha_marc()
                else:
                    col_mostrar = st.session_state.col_respuesta_rapida
                    for r in resultados[col_mostrar].unique():
                        st.write(f"✅ {r}")
            else:
                st.warning(f"No se encontró nada en '{filtro_mat}'.")
                c_sug = col_busq
                df_f = df[df["Material"] == filtro_mat] if filtro_mat != "Todos" else df
                posibles = df_f[c_sug].dropna().unique().tolist()
                sug = get_close_matches(user_input, posibles, n=3, cutoff=0.4)
                if sug:
                    st.info("¿Quizás buscabas?")
                    cols = st.columns(len(sug))
                    for i, s in enumerate(sug):
                        cols[i].button(s, on_click=aplicar_sugerencia, args=(s, c_sug, df, filtro_mat))

elif modo_app == "✍️ Módulo de Catalogación":
    st.title("✍️ Catalogación")
    if not st.session_state.autenticado:
        st.info("🔒 Identifícate")
        st.text_input("Contraseña:", type="password", key="password_input")
        st.button("Entrar", on_click=comprobar_login)
        if st.session_state.error_pass: st.error("Incorrecta")
    else:
        st.success("🔓 Sesión iniciada")
        st.button("Cerrar Sesión", on_click=cerrar_sesion)
        st.divider()

        with st.form("catalogacion", clear_on_submit=True):
            nuevo_mat = st.selectbox("Colección", ["Monografías", "Ilustrados", "Cómics"])
            c1, c2 = st.columns(2)
            with c1:
                n20 = st.text_input("20 - ISBN")
                n100 = st.text_input("100 - Autor")
                n245 = st.text_input("245 - Título")
            with c2:
                n260 = st.text_input("260 - Publicación")
                n300 = st.text_input("300 - Descripción Física")
                n650 = st.text_input("650 - Materias")
            
            if st.form_submit_button("💾 Guardar"):
                if n245:
                    reg = {"Material": nuevo_mat, "20": n20, "100": n100, "245": n245, "260": n260, "300": n300, "650": n650}
                    df = pd.concat([df, pd.DataFrame([reg])], ignore_index=True)
                    df.to_excel("biblioteca.xlsx", index=False)
                    st.cache_data.clear()
                    st.success("¡Guardado!")
