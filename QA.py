import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
import re
import requests

# ==========================================
# 1. CONFIGURACIÓN INICIAL
# ==========================================
st.set_page_config(page_title="Biblioteca OMEGAHOME Cloud", layout="wide", page_icon="☁️📚")

try:
    SHEET_URL = st.secrets["SHEET_URL"]
except:
    st.error("Falta configurar la SHEET_URL en los Secrets de Streamlit.")

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
        st.error(f"Error al conectar con Google Sheets: {e}")
        return pd.DataFrame()

# ==========================================
# 2. FUNCIONES DE BÚSQUEDA Y FICHA
# ==========================================
def extraer_entidad(pregunta):
    ruido = ["QUÉ", "QUE", "QUIÉN", "QUIEN", "DÓNDE", "DONDE", "CUÁNDO", "CUANDO", 
             "CÓMO", "COMO", "CUÁNTO", "CUANTO", "ISBN", "ESCRIBIÓ", "ESCRIBIO", "DE", "EL", "LA"]
    palabras = pregunta.replace("?", "").replace("¿", "").split()
    return " ".join([p for p in palabras if p.upper() not in ruido]).strip()

def ejecutar_busqueda_exacta(df, columna, termino, filtro_material):
    if df.empty: return df
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
        orden_etiquetas = ["Material", "090", "020", "100", "245", "260", "300", "650"]
        columnas_disponibles = [col for col in orden_etiquetas if col in reg.columns]
        reg = reg[columnas_disponibles].dropna(axis=1, how='all')
        
        ficha = reg.T
        ficha.columns = ["Contenido"]
        st.table(ficha)

# ==========================================
# 3. ESTADOS DE SESIÓN (MEMORIA)
# ==========================================
if 'indice_registro' not in st.session_state: st.session_state.indice_registro = 0
if 'resultados_actuales' not in st.session_state: st.session_state.resultados_actuales = pd.DataFrame()
if 'ultima_q' not in st.session_state: st.session_state.ultima_q = ""
if 'ultimo_filtro_mat' not in st.session_state: st.session_state.ultimo_filtro_mat = ""
if 'autenticado' not in st.session_state: st.session_state.autenticado = False

# Variables para auto-rellenar la catalogación
for key in ['isbn_temp', 'titulo_temp', 'autor_temp', 'pub_temp', 'desc_temp', 'mat_temp']:
    if key not in st.session_state:
        st.session_state[key] = ""

df = cargar_datos_cloud()

# ==========================================
# 4. BARRA LATERAL (NAVEGACIÓN)
# ==========================================
st.sidebar.title("🏛️ Biblioteca Cloud")
modo_app = st.sidebar.radio("Navegación:", ["🔍 OPAC", "✍️ Catalogación", "📸 Catalogación Automática"])
if st.sidebar.button("🔄 Forzar Sincronización"):
    st.cache_data.clear()
    st.rerun()

# ==========================================
# MÓDULO 1: OPAC (BUSCADOR)
# ==========================================
if modo_app == "🔍 OPAC":
    st.title("📚 Buscador Online")
    filtro_mat = st.radio("Colección:", ["Todos", "Monografías", "Ilustrados", "Cómics"], horizontal=True)
    
    modo_busq = st.selectbox("Buscar por:", ["General (Taxonomía)", "Materias (Etiqueta 650)"])
    user_input = st.text_input("¿Qué buscas?")

    if user_input and not df.empty:
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

            if col_b not in df.columns: col_b = "245"
            if col_r not in df.columns: col_r = "245"

            st.session_state.resultados_actuales = ejecutar_busqueda_exacta(df, col_b, ent, filtro_mat)
            st.session_state.col_rapida = col_r

        res = st.session_state.resultados_actuales
        if not res.empty:
            st.success(f"Encontrados {len(res)} registros.")
            if st.checkbox("Ver Ficha Técnica"): mostrar_ficha_marc()
            else:
                for idx, row in res.drop_duplicates(subset=[st.session_state.col_rapida]).iterrows():
                    val = row[st.session_state.col_rapida]
                    tejuelo = f" 🏷️ **[{row['090']}]** " if "090" in row and pd.notna(row["090"]) else ""
                    st.write(f"✅{tejuelo} {val}")

# ==========================================
# MÓDULO 2: CATALOGACIÓN MANUAL
# ==========================================
elif modo_app == "✍️ Catalogación":
    st.title("✍️ Registro Manual en la Nube")
    
    if not st.session_state.autenticado:
        pwd = st.text_input("Clave de acceso:", type="password", key="pwd_manual")
        if st.button("Acceder", key="btn_manual"):
            if pwd == "1234":
                st.session_state.autenticado = True
                st.rerun()
            else: st.error("Clave incorrecta")
    else:
        st.button("Cerrar Sesión", on_click=lambda: st.session_state.update({"autenticado": False}), key="logout_manual")
        
        st.info("💡 Rellena los datos manualmente. Ideal para libros antiguos sin código de barras.")
        
        with st.form("form_cat_manual", clear_on_submit=True):
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
                
            if st.form_submit_button("💾 Guardar Manualmente"):
                if not n245 or not n090:
                    st.warning("⚠️ ¡Atención! Los campos '090 - Tejuelo' y '245 - Título' son obligatorios.")
                else:
                    try:
                        sheet = conectar_google()
                        nueva_fila = [nuevo_m, n090, n020, n100, n245, n260, n300, n650]
                        sheet.append_row(nueva_fila)
                        st.cache_data.clear()
                        st.success(f"✅ ¡El libro '{n245}' se ha guardado manualmente!")
                    except Exception as e:
                        st.error(f"Error al guardar: {e}")

# ==========================================
# MÓDULO 3: CATALOGACIÓN AUTOMÁTICA
# ==========================================
elif modo_app == "📸 Catalogación Automática":
    st.title("📸 Auto-Catalogación")
    
    if not st.session_state.autenticado:
        pwd = st.text_input("Clave de acceso:", type="password", key="pwd_auto")
        if st.button("Acceder", key="btn_auto"):
            if pwd == "1234":
                st.session_state.autenticado = True
                st.rerun()
            else: st.error("Clave incorrecta")
    else:
        st.button("Cerrar Sesión", on_click=lambda: st.session_state.update({"autenticado": False}), key="logout_auto")
        
        # Función mejorada de conexión a la API de Google Books
        def buscar_datos_api(isbn):
            url_estricta = f"https://www.googleapis.com/books/v1/volumes?q=isbn:{isbn}"
            url_general = f"https://www.googleapis.com/books/v1/volumes?q={isbn}"
            
            for url in [url_estricta, url_general]:
                try:
                    respuesta = requests.get(url).json()
                    if "items" in respuesta and len(respuesta["items"]) > 0:
                        info = respuesta["items"][0]["volumeInfo"]
                        st.session_state.titulo_temp = info.get("title", "")
                        st.session_state.autor_temp = ", ".join(info.get("authors", []))
                        st.session_state.pub_temp = f"{info.get('publisher', '')}, {info.get('publishedDate', '')}".strip(", ")
                        st.session_state.desc_temp = f"{info.get('pageCount', '')} p." if "pageCount" in info else ""
                        st.session_state.mat_temp = ", ".join(info.get("categories", []))
                        return True
                except:
                    pass
            return False

        st.subheader("1️⃣ Buscar el libro en internet")
        st.info("💡 Haz una foto al código de barras o teclea el número manualmente.")
        
        # OPCIÓN A: ESCÁNER CON CÁMARA
        foto = st.camera_input("📸 Escanear ISBN con la cámara")
        
        if foto is not None:
            from PIL import Image
            from pyzbar.pyzbar import decode
            
            img = Image.open(foto)
            codigos = decode(img)
            
            if codigos:
                isbn_leido = codigos[0].data.decode('utf-8')
                st.session_state.isbn_temp = isbn_leido
                
                if buscar_datos_api(isbn_leido):
                    st.success("✅ ¡Libro encontrado! Datos volcados al formulario.")
                else:
                    st.warning(f"⚠️ El ISBN ({isbn_leido}) no está en la base de datos de Google Books.")
            else:
                st.error("⚠️ No se ha detectado ningún código. Intenta enfocar mejor.")
        
        st.write("--- O ---")
        
        # OPCIÓN B: BÚSQUEDA MANUAL FUERA DEL FORMULARIO
        col_b1, col_b2 = st.columns([3, 1])
        with col_b1:
            isbn_manual = st.text_input("⌨️ Teclea el ISBN a mano:")
        with col_b2:
            st.write("") 
            st.write("") 
            if st.button("🔍 Buscar ISBN"):
                if isbn_manual:
                    isbn_limpio = isbn_manual.replace("-", "").strip()
                    st.session_state.isbn_temp = isbn_limpio
                    if buscar_datos_api(isbn_limpio):
                        st.success("✅ ¡Libro encontrado! Datos volcados al formulario de abajo.")
                    else:
                        st.warning(f"⚠️ El ISBN {isbn_limpio} no se encontró en Google Books.")
                else:
                    st.warning("Escribe un ISBN primero.")

        st.divider()

        # PASO 2: GUARDADO
        st.subheader("2️⃣ Revisar y Guardar")
        with st.form("form_cat_auto", clear_on_submit=True):
            nuevo_m = st.selectbox("Material", ["Monografías", "Ilustrados", "Cómics"])
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
                
            if st.form_submit_button("💾 Guardar en Google Sheets"):
                if not n245 or not n090:
                    st.warning("⚠️ ¡Atención! Los campos '090 - Tejuelo' y '245 - Título' son obligatorios.")
                else:
                    try:
                        sheet = conectar_google()
                        nueva_fila = [nuevo_m, n090, n020, n100, n245, n260, n300, n650]
                        sheet.append_row(nueva_fila)
                        
                        st.cache_data.clear()
                        for key in ['isbn_temp', 'titulo_temp', 'autor_temp', 'pub_temp', 'desc_temp', 'mat_temp']:
                            st.session_state[key] = ""
                            
                        st.success(f"✅ ¡El libro '{n245}' se ha guardado y sincronizado correctamente!")
                    except Exception as e:
                        st.error(f"Error al guardar: {e}")
