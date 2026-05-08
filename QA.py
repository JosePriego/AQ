import streamlit as st
import pandas as pd

# 1. Mapeo basado en tu taxonomía
MAPEO_MARC = {
    "QUIÉN": ["100", "110", "111", "700", "710"],
    "QUÉ": ["245"],
    "DÓNDE": ["260"],
    "CUÁNDO": ["260"],
    "CÓMO": ["300", "600", "610", "650"]
}

@st.cache_data
def cargar_datos_excel():
    try:
        # IMPORTANTE: Cambiamos a read_excel y forzamos que todo sea texto (dtype=str)
        # para que las etiquetas 100, 245, etc., se lean correctamente.
        df = pd.read_excel("biblioteca.xlsx", dtype=str)
        return df
    except Exception as e:
        st.error(f"Error al cargar el archivo: {e}")
        return pd.DataFrame()

def extraer_termino_limpio(pregunta):
    # Palabras que queremos eliminar de la pregunta para quedarnos con el nombre o título
    ruido = ["QUÉ", "QUE", "QUIÉN", "QUIEN", "DÓNDE", "DONDE", "ESCRIBIÓ", "ESCRIBIO", "EL", "LA", "DE", "DEL"]
    palabras = pregunta.upper().replace("?", "").replace("¿", "").split()
    filtrado = [p for p in palabras if p not in ruido]
    return " ".join(filtrado)

# --- INTERFAZ STREAMLIT ---
st.set_page_config(page_title="Buscador MARC-21", page_icon="📚")
st.title("📚 Sistema de Recuperación Bibliotecaria")

df = cargar_datos_excel()

if not df.empty:
    pregunta_usuario = st.text_input("Introduce tu pregunta (ej: ¿Qué escribió Waldron?):")

    if pregunta_usuario:
        pregunta_up = pregunta_usuario.upper()
        
        # 1. Identificar P-Clase
        clase_detectada = None
        if "QUIÉN" in pregunta_up or "QUIEN" in pregunta_up: clase_detectada = "QUIÉN"
        elif "QUÉ" in pregunta_up or "QUE" in pregunta_up: clase_detectada = "QUÉ"
        elif "DÓNDE" in pregunta_up or "DONDE" in pregunta_up: clase_detectada = "DÓNDE"

        if clase_detectada:
            termino = extraer_termino_limpio(pregunta_usuario)
            st.info(f"Detectada intención: **{clase_detectada}**. Buscando: *{termino}*")

            # 2. Lógica de búsqueda cruzada
            # Si pregunta "QUÉ", el usuario nos da un autor (100) y quiere el título (245)
            if clase_detectada == "QUÉ":
                cols_donde_buscar = ["100", "110", "700"]
                col_que_mostrar = "245"
            # Si pregunta "QUIÉN", el usuario nos da un título (245) y quiere el autor (100)
            elif clase_detectada == "QUIÉN":
                cols_donde_buscar = ["245"]
                col_que_mostrar = "100"
            else:
                cols_donde_buscar = ["245"]
                col_que_mostrar = MAPEO_MARC[clase_detectada][0]

            # 3. Ejecutar la búsqueda en el DataFrame
            hallado = False
            for col in cols_donde_buscar:
                if col in df.columns:
                    # Buscamos coincidencias parciales (case=False para ignorar mayúsculas)
                    mask = df[col].str.contains(termino, case=False, na=False)
                    resultados = df[mask]
                    
                    if not resultados.empty:
                        for valor in resultados[col_que_mostrar].unique():
                            st.success(f"**Resultado ({col_que_mostrar}):** {valor}")
                        hallado = True
                        break
            
            if not hallado:
                st.warning(f"No se encontró nada relacionado con '{termino}' en los campos de {clase_detectada}.")
        else:
            st.error("Por favor, usa palabras como 'Qué', 'Quién' o 'Dónde'.")
else:
    st.warning("Carga un archivo llamado 'biblioteca.xlsx' en la raíz del proyecto.")
