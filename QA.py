import streamlit as st
import pandas as pd
import re
from difflib import get_close_matches
import os
import io

# 1. Configuración de la página
st.set_page_config(page_title="Biblioteca de OMEGAHOME", layout="wide", page_icon="🏠📚")

# 2. Carga de datos
@st.cache_data
def cargar_datos():
    try:
        if not os.path.exists("biblioteca.xlsx"):
            # Añadimos la columna 090 para el tejuelo
            df_vacio = pd.DataFrame(columns=["Material", "090", "020", "100", "245", "260", "300", "650"])
            df_vacio.to_excel("biblioteca.xlsx", index=False)
            return df_vacio
        df = pd.read_excel("biblioteca.xlsx", dtype=str)
        df.columns = [str(c).strip() for c in df.columns]
        return df
    except Exception as e:
        st.error(f"Error al cargar la base de datos: {e}")
        return None

# 3. Lógica de Búsqueda
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

# 4. Interfaz de Ficha MARC
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
        
        # Añadimos la 090 al orden prioritario
        orden_etiquetas = ["Material", "090", "020", "100", "245", "260", "300", "650"]
        columnas_disponibles = [col for col in orden_etiquetas if col in reg.columns]
        
        otras_columnas = [col for col in reg.columns if col not in orden_etiquetas and "." not in col and "Unnamed" not in col]
        
        reg = reg[columnas_disponibles + otras_columnas]
        reg = reg.dropna(axis=1, how='all')

        if "100" in reg.columns:
            val = reg.iloc[0]["100"]
            if pd.isna(val) or str(val).strip().lower() in ["nan", ""]:
                reg["100"] = "Anónimo"

        ficha = reg.T
        ficha.columns = ["Contenido"]
        ficha.index.name = "Etiqueta MARC"
        st.table(ficha)

# --- ESTADOS DE SESIÓN ---
if 'indice_registro' not in st.session_state: st.session_state.indice_registro = 0
if 'resultados_actuales' not in st.session_state: st.session_state.resultados_actuales = pd.DataFrame()
if 'ultima_q' not in st.session_state: st.session_state.ultima_q = ""
if 'ultimo_filtro_mat' not in st.session_state: st.session_state.ultimo_filtro_mat = ""
if 'autenticado' not in st.session_state: st.session_state.autenticado = False

df = cargar_datos()

# --- BARRA LATERAL ---
st.sidebar.title("🏛️ Mi Biblioteca")
modo_app = st.sidebar.radio("Navegación:", ["🔍 OPAC", "✍️ Módulo de Catalogación"])
st.sidebar.divider()

# ==========================================
# OPAC
# ==========================================
if modo_app == "🔍 OPAC":
    st.title("📚 Buscador")
    
    filtro_mat = st.radio("Colección:", ["Todos", "Monografías", "Ilustrados", "Cómics"], horizontal=True)
    st.divider()
    
    modo_busq = st.selectbox("Buscar por:", ["General (Taxonomía)", "Materias (Etiqueta 650)"])
    user_input = st.text_input("¿Qué buscas?")

    if user_input:
        if st.session_state.ultima_q != user_input or st.session_state.ultimo_filtro_mat != filtro_mat:
            st.session_state.indice_registro = 0
            st.session_state.ultima_q = user_input
            st.session_state.ultimo_filtro_mat = filtro_mat
            
            if modo_busq == "Materias (Etiqueta 650)":
                col_b, col_r = "650", "245"
                ent = user_input.strip()
            else:
                p_up = user_input.upper()
                ent = extraer_entidad(user_input)
                if "ISBN" in p_up: col_b, col_r = "020", "245"
                elif any(w in p_up for w in ["QUIÉN", "QUIEN"]): col_b, col_r = "245", "100"
                elif any(w in p_up for w in ["QUÉ", "QUE"]): col_b, col_r = "100", "245"
                else: col_b, col_r = "245", "100"

            st.session_state.resultados_actuales = ejecutar_busqueda_exacta(df, col_b, ent, filtro_mat)
            st.session_state.col_rapida = col_r

        res = st.session_state.resultados_actuales
        if not res.empty:
            st.success(f"Encontrados {len(res)} libros en '{filtro_mat}'.")
            if st.checkbox("Ver Ficha Técnica"):
                mostrar_ficha_marc()
            else:
                # Mostrar resultados rápidos con el Tejuelo si existe
                for idx, row in res.drop_duplicates(subset=[st.session_state.col_rapida]).iterrows():
                    valor_principal = row[st.session_state.col_rapida]
                    
                    # Comprobamos si tiene tejuelo para mostrarlo en la vista rápida
                    tejuelo = ""
                    if "090" in row and not pd.isna(row["090"]) and str(row["090"]).strip() not in ["", "nan"]:
                        tejuelo = f" 🏷️ **[{row['090']}]** "
                    
                    # Lógica para Anónimos en la vista rápida
                    if (pd.isna(valor_principal) or str(valor_principal).lower() == "nan") and st.session_state.col_rapida == "100":
                        st.write(f"✅{tejuelo} Autor: Anónimo")
                    else:
                        st.write(f"✅{tejuelo} {valor_principal}")
        else:
            st.warning("No hay resultados.")
            c_sug = "650" if modo_busq == "Materias (Etiqueta 650)" else "245"
            df_f = df[df["Material"] == filtro_mat] if filtro_mat != "Todos" else df
            posibles = df_f[c_sug].dropna().unique().tolist()
            sug = get_close_matches(user_input, posibles, n=3, cutoff=0.4)
            if sug:
                st.info("¿Quizás buscabas...?")
                cols = st.columns(len(sug))
                for i, s in enumerate(sug):
                    if cols[i].button(s):
                        st.session_state.resultados_actuales = df_f[df_f[c_sug] == s]
                        st.rerun()

# ==========================================
# CATALOGACIÓN
# ==========================================
elif modo_app == "✍️ Módulo de Catalogación":
    st.title("✍️ Módulo de Catalogación")
    
    if not st.session_state.autenticado:
        pwd = st.text_input("Introduce la clave de la biblioteca:", type="password")
        if st.button("Acceder"):
            if pwd == "1234":
                st.session_state.autenticado = True
                st.rerun()
            else: st.error("Clave incorrecta")
    else:
        st.button("Cerrar Sesión", on_click=lambda: st.session_state.update({"autenticado": False}))
        
        with st.form("form_cat", clear_on_submit=True):
            nuevo_m = st.selectbox("Tipo de Material", ["Monografías", "Ilustrados", "Cómics"])
            
            # Formulario reorganizado para hacerle hueco al tejuelo (090)
            c1, c2 = st.columns(2)
            with c1:
                n090 = st.text_input("090 - Tejuelo (Signatura)")
                n100 = st.text_input("100 - Autor")
                n260 = st.text_input("260 - Publicación")
                n650 = st.text_input("650 - Materias")
            with c2:
                n020 = st.text_input("020 - ISBN")
                n245 = st.text_input("245 - Título")
                n300 = st.text_input("300 - Desc. Física")
                
            if st.form_submit_button("💾 Guardar"):
                if n245:
                    nuevo_r = {"Material": nuevo_m, "090": n090, "020": n020, "100": n100, "245": n245, "260": n260, "300": n300, "650": n650}
                    df = pd.concat([df, pd.DataFrame([nuevo_r])], ignore_index=True)
                    df.to_excel("biblioteca.xlsx", index=False)
                    st.cache_data.clear()
                    st.success("Libro guardado con éxito.")
        
        st.divider()
        st.subheader("Copia de Seguridad")
        buffer = io.BytesIO()
        with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
            df.to_excel(writer, index=False)
        st.download_button("📥 Descargar Excel Actualizado", buffer.getvalue(), "biblioteca.xlsx", "application/vnd.ms-excel")
