import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
import re
import io

# 1. Configuración de la página
st.set_page_config(page_title="Biblioteca OMEGAHOME Cloud", layout="wide", page_icon="☁️📚")

# --- CONFIGURACIÓN DE GOOGLE SHEETS ---
JSON_FILE = "biblioteca-496011-b8f3cb8880ac.json"
# ⚠️ PEGA AQUÍ LA URL DE TU HOJA DE GOOGLE SHEETS
SHEET_URL = "https://docs.google.com/spreadsheets/d/1uE74UUnC5NCYr72Gv5zuun8XlA8BtC2gHq3RpV9PNKI/edit?usp=sharing" 

def conectar_google():
    scope = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
    creds = Credentials.from_service_account_file(JSON_FILE, scopes=scope)
    client = gspread.authorize(creds)
    # Abrimos la hoja por URL y seleccionamos la primera pestaña
    sheet = client.open_by_url(SHEET_URL).sheet1
    return sheet

# 2. Carga de datos desde la nube con caché de 10 minutos
@st.cache_data(ttl=600)
def cargar_datos_cloud():
    try:
        sheet = conectar_google()
        data = sheet.get_all_records()
        df = pd.DataFrame(data)
        
        # Normalizar cabeceras (020, Tejuelo, etc.)
        def normalizar_cabecera(col):
            col = str(col).strip()
            if col.isdigit(): return col.zfill(3)
            return col
            
        df.columns = [normalizar_cabecera(c) for c in df.columns]
        return df.astype(str) # Forzamos todo a texto para evitar líos con Excel
    except Exception as e:
        st.error(f"Error al conectar con Google Sheets: {e}")
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
            if c1.button("⬅️ Anterior"): st.session_state.indice_registro = max(0, st.session_state.indice_registro - 1)
            c2.markdown(f"<h3 style='text-align: center;'>Registro {st.session_state.indice_registro + 1} de {total}</h3>", unsafe_allow_html=True)
            if c3.button("Siguiente ➡️"): st.session_state.indice_registro = min(total - 1, st.session_state.indice_registro + 1)
        
        reg = resultados.iloc[[st.session_state.indice_registro]].copy()
        orden_etiquetas = ["Material", "Tejuelo", "020", "100", "245", "260", "300", "650"]
        columnas_disponibles = [col for col in orden_etiquetas if col in reg.columns]
        reg = reg[columnas_disponibles].dropna(axis=1, how='all')
        
        ficha = reg.T
        ficha.columns = ["Contenido"]
        st.table(ficha)

# --- ESTADOS ---
if 'indice_registro' not in st.session_state: st.session_state.indice_registro = 0
if 'resultados_actuales' not in st.session_state: st.session_state.resultados_actuales = pd.DataFrame()
if 'ultima_q' not in st.session_state: st.session_state.ultima_q = ""
if 'ultimo_filtro_mat' not in st.session_state: st.session_state.ultimo_filtro_mat = ""
if 'autenticado' not in st.session_state: st.session_state.autenticado = False

df = cargar_datos_cloud()

# --- BARRA LATERAL ---
st.sidebar.title("🏛️ Biblioteca Cloud")
modo_app = st.sidebar.radio("Navegación:", ["🔍 OPAC", "✍️ Catalogación"])
if st.sidebar.button("🔄 Forzar Sincronización"):
    st.cache_data.clear()
    st.rerun()

if modo_app == "🔍 OPAC":
    st.title("📚 Buscador Online")
    filtro_mat = st.radio("Colección:", ["Todos", "Monografías", "Ilustrados", "Cómics"], horizontal=True)
    
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
            st.success(f"Encontrados {len(res)} registros.")
            if st.checkbox("Ver Ficha Técnica"): mostrar_ficha_marc()
            else:
                for idx, row in res.drop_duplicates(subset=[st.session_state.col_rapida]).iterrows():
                    val = row[st.session_state.col_rapida]
                    tejuelo = f" 🏷️ **[{row['Tejuelo']}]** " if "Tejuelo" in row and pd.notna(row["Tejuelo"]) else ""
                    st.write(f"✅{tejuelo} {val}")

elif modo_app == "✍️ Catalogación":
    st.title("✍️ Registro en la Nube")
    if not st.session_state.autenticado:
        pwd = st.text_input("Clave de acceso:", type="password")
        if st.button("Acceder"):
            if pwd == "1234":
                st.session_state.autenticado = True
                st.rerun()
            else: st.error("Clave incorrecta")
    else:
        st.button("Cerrar Sesión", on_click=lambda: st.session_state.update({"autenticado": False}))
        with st.form("form_cat", clear_on_submit=True):
            nuevo_m = st.selectbox("Material", ["Monografías", "Ilustrados", "Cómics"])
            c1, c2 = st.columns(2)
            with c1:
                nTejuelo = st.text_input("Tejuelo")
                n100 = st.text_input("100 - Autor")
                n260 = st.text_input("260 - Publicación")
                n650 = st.text_input("650 - Materias")
            with c2:
                n020 = st.text_input("020 - ISBN")
                n245 = st.text_input("245 - Título")
                n300 = st.text_input("300 - Desc. Física")
                
            if st.form_submit_button("💾 Guardar directamente en Google Sheets"):
                if n245:
                    try:
                        sheet = conectar_google()
                        # IMPORTANTE: El orden de esta lista debe ser igual al de las columnas de tu Google Sheet
                        nueva_fila = [nuevo_m, nTejuelo, n020, n100, n245, n260, n300, n650]
                        sheet.append_row(nueva_fila)
                        
                        st.cache_data.clear() # Limpiamos la memoria para que la búsqueda vea el nuevo libro
                        st.success("✅ ¡Libro guardado y sincronizado con la nube!")
                    except Exception as e:
                        st.error(f"Error al conectar con la nube: {e}")
