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
        # Cargamos el Excel. Asegúrate de que el archivo esté en la misma carpeta.
        df = pd.read_excel("biblioteca.xlsx", dtype=str)
        # Limpiamos espacios en blanco en los nombres de las columnas
        df.columns = [str(c).strip() for c in df.columns]
        return df
    except Exception as e:
        st.error(f"Error crítico: No se pudo cargar 'biblioteca.xlsx'. {e}")
        return None

# 3. Funciones de apoyo
def extraer_entidad(pregunta):
    """Limpia la pregunta para extraer el término de búsqueda (autor, título, etc.)"""
    ruido = ["QUÉ", "QUE", "QUIÉN", "QUIEN", "DÓNDE", "DONDE", "CUÁNDO", "CUANDO", 
             "CÓMO", "COMO", "CUÁNTO", "CUANTO", "ISBN", "ESCRIBIÓ", "ESCRIBIO", "DE", "EL", "LA"]
    palabras = pregunta.replace("?", "").replace("¿", "").split()
    return " ".join([p for p in palabras if p.upper() not in ruido]).strip()

def ejecutar_busqueda_exacta(df, columna, termino):
    """Busca palabras completas usando Regex para evitar falsos positivos"""
    # Escapamos el término por si tiene caracteres especiales
    termino_esc = re.escape(termino)
    # \b marca el límite de palabra (evita que 'war' encuentre 'software')
    patron = rf"\b{termino_esc}\b"
    
    try:
        mask = df[columna].str.contains(patron, case=False, na=False, regex=True)
        return df[mask]
    except:
        # Fallback por si el término no es compatible con Regex
        return df[df[columna].str.contains(termino, case=False, na=False)]

def mostrar_ficha_marc():
    """Renderiza la ficha técnica vertical con navegación"""
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
        
        # Obtener el registro actual
        reg = resultados.iloc[[st.session_state.indice_registro]].copy()
        
        # Aplicar lógica de Anónimo en el campo 100
        if "100" in reg.columns:
            val = reg.iloc[0]["100"]
            if pd.isna(val) or str(val).strip().lower() in ["nan", ""]:
                reg["100"] = "Anónimo"

        # Transposición para ver columnas como filas
        ficha = reg.T
        ficha.columns = ["Información Bibliográfica"]
        ficha.index.name = "Etiqueta MARC"
        
        st.table(ficha)

# --- INICIALIZACIÓN DE VARIABLES DE ESTADO ---
if 'indice_registro' not in st.session_state: st.session_state.indice_registro = 0
if 'resultados_actuales' not in st.session_state: st.session_state.resultados_actuales = pd.DataFrame()
if 'ultima_q' not in st.session_state: st.session_state.ultima_q = ""

# --- CUERPO DE LA APLICACIÓN ---
st.title("📚 Sistema de Recuperación de Información")
st.markdown("Basado en aproximación teórica de preguntas-respuestas y formato MARC21.")

df = cargar_datos()

if df is not None:
    # Barra lateral de navegación
    with st.sidebar:
        st.header("Configuración")
        modo = st.radio("Selecciona el motor de búsqueda:", 
                        ["General (Taxonomía)", "Materias (Etiqueta 650)"])
        st.divider()
        st.info("💡 **Consejo:** En el modo materias, escribe el concepto directo (ej. Historia). En modo General, puedes preguntar '¿Quién escribió...?'")

    # Entrada de usuario
    placeholder = "¿Quién escribió...?" if modo == "General (Taxonomía)" else "[Poner solo la materia a recuperar]"
    user_input = st.text_input("Buscador:", placeholder=placeholder)

    if user_input:
        # Detectar si la pregunta ha cambiado para resetear el buscador
        if st.session_state.ultima_q != user_input:
            st.session_state.indice_registro = 0
            st.session_state.ultima_q = user_input
            
            # Definición de etiquetas MARC según la pregunta
            if modo == "Materias (Etiqueta 650)":
                col_busq, col_res = "650", "245"
                entidad = user_input.strip()
            else:
                p_up = user_input.upper()
                entidad = extraer_entidad(user_input)
                
                # Taxonomía lógica
                if "ISBN" in p_up: col_busq, col_res = "20", "245"
                elif any(w in p_up for w in ["QUIÉN", "QUIEN"]): col_busq, col_res = "245", "100"
                elif any(w in p_up for w in ["QUÉ", "QUE"]): col_busq, col_res = "100", "245"
                elif any(w in p_up for w in ["DÓNDE", "DONDE", "CUÁNDO", "CUANDO"]): col_busq, col_res = "245", "260"
                elif any(w in p_up for w in ["CÓMO", "COMO", "CUÁNTO", "CUANTO"]): col_busq, col_res = "245", "300"
                else: col_busq, col_res = "245", "100" # Por defecto autor

            # Ejecutar búsqueda con protección de palabra exacta
            st.session_state.resultados_actuales = ejecutar_busqueda_exacta(df, col_busq, entidad)
            st.session_state.col_respuesta_rapida = col_res # Guardamos para la vista previa

        # --- MOSTRAR RESULTADOS ---
        resultados = st.session_state.resultados_actuales
        
        if not resultados.empty:
            st.write(f"Se han encontrado **{len(resultados)}** coincidencias.")
            
            ver_marc = st.checkbox("🔍 Visualizar Ficha Técnica MARC21 (Modo vertical)")
            
            if ver_marc:
                mostrar_ficha_marc()
            else:
                # Vista rápida de resultados (títulos o autores)
                for r in resultados[st.session_state.col_respuesta_rapida].unique():
                    if (pd.isna(r) or str(r).lower() == "nan") and st.session_state.col_respuesta_rapida == "100":
                        st.success("✅ Autor: Anónimo")
                    else:
                        st.success(f"✅ {r}")
        else:
            # Sistema de sugerencias si no hay resultados
            st.warning(f"No se encontró el término '{user_input}' exacto.")
            
            # Buscamos en la columna que tocaba según el modo
            if modo == "Materias (Etiqueta 650)": c_sug = "650"
            else: c_sug = "245"
            
            posibles = df[c_sug].dropna().unique().tolist()
            sug = get_close_matches(user_input, posibles, n=3, cutoff=0.4)
            
            if sug:
                st.info("¿Quizás buscabas algo de esto?")
                cols = st.columns(len(sug))
                for i, s in enumerate(sug):
                    if cols[i].button(s):
                        # Si pulsa la sugerencia, forzamos la búsqueda de ese término
                        st.session_state.resultados_actuales = df[df[c_sug] == s]
                        st.rerun()
            else:
                st.error("No hay registros ni sugerencias similares en la base de datos.")
else:
    st.info("Esperando el archivo 'biblioteca.xlsx' para comenzar...")
