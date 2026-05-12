import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
import re
import requests
from difflib import get_close_matches
from PIL import Image

# ==========================================
# 1. CONFIGURACIÓN E INTERFAZ INICIAL
# ==========================================
st.set_page_config(page_title="Biblioteca OMEGAHOME Cloud", layout="wide", page_icon="☁️📚")

# Intentar obtener la URL de los secretos
try:
    SHEET_URL = st.secrets["SHEET_URL"]
except:
    st.error("⚠️ Falta configurar la SHEET_URL en los Secrets de Streamlit.")

def conectar_google():
    creds_dict = {
        "type": st.secrets["gcp_service_account"]["type"],
        "project_id": st.secrets["gcp_service_account"]["project_id"],
        "private_key_id": st.secrets["gcp_service_account"]["private_key_id"],
        "private_key": st.secrets["gcp_service_account"]["private_key"],
        "client_email": st.secrets["gcp_service_account"]["client_email"],
        "client_id": st.secrets["gcp_service_account"]["client_id"],
        "auth_uri": st.secrets["gcp_service_account"]["auth_uri"],
        "token_uri": st.secrets["gcp_service_account"]["token_uri"],
        "auth_provider_x509_cert_url": st.secrets["gcp_service_account"]["auth_provider_x509_cert_url"],
        "client_x509_cert_url": st.secrets["gcp_service_account"]["client_x509_cert_url"],
    }
    scope = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
    creds = Credentials.from_service_account_info(creds_dict, scopes=scope)
    client = gspread.authorize(creds)
    sheet = client.open_by_url(SHEET_URL).sheet1
    return sheet

@st.cache_data(ttl=600)
def cargar_datos_cloud():
    try:
        sheet = conectar_google()
        data = sheet.get_all_records()
        df = pd.DataFrame(data)
        
        def normalizar_cabecera(col):
            col = str(col).strip()
            if col.isdigit(): return col.zfill(3)
            return col
            
        df.columns = [normalizar_cabecera(c) for c in df.columns]
        return df.astype(str)
    except Exception as e:
        st.error(f"Error al conectar con la base de datos: {e}")
        return pd.DataFrame()

# ==========================================
# 2. FUNCIONES DE APOYO (OPAC Y FICHA)
# ==========================================
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
        orden_etiquetas = ["Material", "090", "020", "100", "245", "260", "300", "650"]
        columnas_disponibles = [col for col in orden_etiquetas if col in reg.columns]
        reg = reg[columnas_disponibles].dropna(axis=1, how='all')
        
        ficha = reg.T
        ficha.columns = ["Contenido"]
        st.table(ficha)

# ==========================================
# 3. ESTADOS DE SESIÓN
# ==========================================
if 'indice_registro' not in st.session_state: st.session_state.indice_registro = 0
if 'resultados_actuales' not in st.session_state: st.session_state.resultados_actuales = pd.DataFrame()
if 'autenticado' not in st.session_state: st.session_state.autenticado = False

# Variables temporales para catalogación
for key in ['isbn_temp', 'titulo_temp', 'autor_temp', 'pub_temp', 'desc_temp', 'mat_temp']:
    if key not in st.session_state: st.session_state[key] = ""

df = cargar_datos_cloud()

# --- BARRA LATERAL ---
st.sidebar.title("🏛️ Biblioteca Cloud")
modo_app = st.sidebar.radio("Navegación:", ["🔍 OPAC", "✍️ Catalogación Manual", "📸 Catalogación Automática"])
if st.sidebar.button("🔄 Forzar Sincronización"):
    st.cache_data.clear()
    st.rerun()

# ==========================================
# MÓDULO 1: OPAC (BUSCADOR PROFESIONAL)
# ==========================================
if modo_app == "🔍 OPAC":
    st.title("📚 Catálogo Online (OPAC)")
    filtro_mat = st.radio("Filtro de Colección:", ["Todos", "Monografías", "Ilustrados", "Cómics"], horizontal=True)
    st.divider()
    
    c1, c2 = st.columns([1, 3])
    with c1:
        campo_busqueda = st.selectbox("Buscar en:", ["Todos los campos", "Título", "Autor", "ISBN", "Publicación", "Materias"])
    with c2:
        user_input = st.text_input("Término de búsqueda...", placeholder="Ej: Gómez-Jurado, 97884..., Roma...")

    if user_input and not df.empty:
        df_filtrado = df if filtro_mat == "Todos" else df[df["Material"] == filtro_mat]
        
        map_campos = {
            "Título": ["245"], "Autor": ["100"], "ISBN": ["020"],
            "Publicación": ["260"], "Materias": ["650"],
            "Todos los campos": ["245", "100", "020", "260", "650"]
        }
        cols_a_buscar = map_campos[campo_busqueda]
        
        mask = pd.Series(False, index=df_filtrado.index)
        termino_limpio = user_input.strip().lower()
        
        for col in cols_a_buscar:
            if col in df_filtrado.columns:
                mask = mask | df_filtrado[col].str.lower().str.contains(termino_limpio, na=False)
        
        resultados = df_filtrado[mask]
        st.session_state.resultados_actuales = resultados
        
        if not resultados.empty:
            st.success(f"🔍 Encontrados {len(resultados)} registro(s).")
            if st.checkbox("Ver Ficha Técnica Detallada"):
                mostrar_ficha_marc()
            else:
                for idx, row in resultados.iterrows():
                    tejuelo = f" 🏷️ **[{row['090']}]** " if "090" in row and pd.notna(row['090']) else ""
                    st.write(f"✅{tejuelo} **{row.get('245', 'S/T')}** / {row.get('100', 'Anónimo')}")
        else:
            st.warning("⚠️ No hay resultados exactos.")
            # Sugerencias
            todas_palabras = []
            for col in cols_a_buscar:
                if col in df_filtrado.columns:
                    todas_palabras.extend(df_filtrado[col].dropna().astype(str).tolist())
            sugerencias = get_close_matches(user_input, todas_palabras, n=3, cutoff=0.5)
            if sugerencias:
                st.info(f"💡 ¿Quizás quisiste decir: {', '.join(sugerencias)}?")

# ==========================================
# MÓDULO 2: CATALOGACIÓN MANUAL
# ==========================================
elif modo_app == "✍️ Catalogación Manual":
    st.title("✍️ Registro Manual")
    if not st.session_state.autenticado:
        pwd = st.text_input("Clave:", type="password", key="p_man")
        if st.button("Acceder", key="b_man"):
            if pwd == "1234": st.session_state.autenticado = True; st.rerun()
            else: st.error("Clave incorrecta")
    else:
        st.button("Cerrar Sesión", on_click=lambda: st.session_state.update({"autenticado": False}), key="l_man")
        with st.form("form_man", clear_on_submit=True):
            nuevo_m = st.selectbox("Material", ["Monografías", "Ilustrados", "Cómics"])
            c1, c2 = st.columns(2)
            with c1:
                n090 = st.text_input("090 - Tejuelo")
                n100 = st.text_input("100 - Autor")
                n260 = st.text_input("260 - Publicación")
                n650 = st.text_input("650 - Materias")
            with c2:
                n020 = st.text_input("020 - ISBN")
                n245 = st.text_input("245 - Título")
                n300 = st.text_input("300 - Desc. Física")
            if st.form_submit_button("💾 Guardar"):
                if n245 and n090:
                    try:
                        sheet = conectar_google()
                        sheet.append_row([nuevo_m, n090, n020, n100, n245, n260, n300, n650])
                        st.cache_data.clear(); st.success("✅ Guardado.")
                    except Exception as e: st.error(f"Error: {e}")
                else: st.warning("Título y Tejuelo son obligatorios.")

# ==========================================
# MÓDULO 3: CATALOGACIÓN AUTOMÁTICA
# ==========================================
elif modo_app == "📸 Catalogación Automática":
    st.title("📸 Auto-Catalogación")
    if not st.session_state.autenticado:
        pwd = st.text_input("Clave:", type="password", key="p_auto")
        if st.button("Acceder", key="b_auto"):
            if pwd == "1234": st.session_state.autenticado = True; st.rerun()
            else: st.error("Clave incorrecta")
    else:
        st.button("Cerrar Sesión", on_click=lambda: st.session_state.update({"autenticado": False}), key="l_auto")
        
        def buscar_datos_api(isbn):
            # Planes A y B (Google Books)
            urls = [f"https://www.googleapis.com/books/v1/volumes?q=isbn:{isbn}", f"https://www.googleapis.com/books/v1/volumes?q={isbn}"]
            for url in urls:
                try:
                    r = requests.get(url).json()
                    if "items" in r:
                        info = r["items"][0]["volumeInfo"]
                        st.session_state.titulo_temp = info.get("title", "")
                        st.session_state.autor_temp = ", ".join(info.get("authors", []))
                        st.session_state.pub_temp = f"{info.get('publisher', '')}, {info.get('publishedDate', '')}".strip(", ")
                        st.session_state.desc_temp = f"{info.get('pageCount', '')} p." if "pageCount" in info else ""
                        st.session_state.mat_temp = ", ".join(info.get("categories", []))
                        return True
                except: pass
            
            # Plan C (OpenLibrary)
            try:
                url_ol = f"https://openlibrary.org/api/books?bibkeys=ISBN:{isbn}&format=json&jscmd=data"
                r_ol = requests.get(url_ol).json()
                key = f"ISBN:{isbn}"
                if key in r_ol:
                    info = r_ol[key]
                    st.session_state.titulo_temp = info.get("title", "")
                    if "authors" in info: st.session_state.autor_temp = ", ".join([a["name"] for a in info["authors"]])
                    pub = f"{', '.join([p['name'] for p in info.get('publishers', [])])}, {info.get('publish_date', '')}"
                    st.session_state.pub_temp = pub.strip(", ")
                    st.session_state.desc_temp = f"{info.get('number_of_pages', '')} p."
                    if "subjects" in info: st.session_state.mat_temp = ", ".join([s["name"] for s in info["subjects"]][:5])
                    return True
            except: pass
            return False

        st.subheader("1️⃣ Buscar Libro")
        foto = st.camera_input("📸 Escanear código de barras")
        if foto:
            from pyzbar.pyzbar import decode
            dec = decode(Image.open(foto))
            if dec:
                isbn = dec[0].data.decode('utf-8')
                st.session_state.isbn_temp = isbn
                if buscar_datos_api(isbn): st.success("✅ Encontrado.")
                else: st.warning("No encontrado en internet.")
        
        st.write("--- O ---")
        c_i1, c_i2 = st.columns([3, 1])
        with c_i1: isbn_m = st.text_input("⌨️ Introducir ISBN manual:")
        with c_i2: 
            st.write(" "); st.write(" ")
            if st.button("🔍 Buscar"):
                isbn_l = isbn_m.replace("-", "").strip()
                st.session_state.isbn_temp = isbn_l
                if buscar_datos_api(isbn_l): st.success("✅ Encontrado.")
                else: st.warning("No encontrado.")

        st.divider()
        st.subheader("2️⃣ Revisar y Guardar")
        with st.form("form_auto", clear_on_submit=True):
            nuevo_m = st.selectbox("Material", ["Monografías", "Ilustrados", "Cómics"], key="m_a")
            c1, c2 = st.columns(2)
            with c1:
                n090 = st.text_input("090 - Tejuelo")
                n100 = st.text_input("100 - Autor", value=st.session_state.autor_temp)
                n260 = st.text_input("260 - Publicación", value=st.session_state.pub_temp)
                n650 = st.text_input("650 - Materias", value=st.session_state.mat_temp)
            with c2:
                n020 = st.text_input("020 - ISBN", value=st.session_state.isbn_temp)
                n245 = st.text_input("245 - Título", value=st.session_state.titulo_temp)
                n300 = st.text_input("300 - Desc. Física", value=st.session_state.desc_temp)
            if st.form_submit_button("💾 Guardar en Cloud"):
                if n245 and n090:
                    try:
                        sheet = conectar_google()
                        sheet.append_row([nuevo_m, n090, n020, n100, n245, n260, n300, n650])
                        st.cache_data.clear()
                        for k in ['isbn_temp', 'titulo_temp', 'autor_temp', 'pub_temp', 'desc_temp', 'mat_temp']: st.session_state[k] = ""
                        st.success("✅ Guardado y sincronizado.")
                    except Exception as e: st.error(f"Error: {e}")
                else: st.warning("Título y Tejuelo son obligatorios.")
