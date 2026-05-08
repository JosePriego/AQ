import streamlit as st
import pandas as pd

# 1. Configuración de la Taxonomía (según tu imagen)
# Mapeamos la P-clase con las etiquetas MARC-21 correspondientes
TAXONOMIA_MARC = {
    "QUIÉN": ["100", "110", "111", "700", "710"],
    "QUÉ": ["245", "260"],
    "DÓNDE": ["260"],
    "CUÁNDO": ["260"],
    "CÓMO": ["300", "6XX"],
    "CUÁNTO": ["300"]
}

# Carga de datos (Simulada para el ejemplo, asegúrate de tener tu xlsx)
@st.cache_data
def cargar_datos():
    # En producción: df = pd.read_excel("biblioteca.xlsx")
    # Ejemplo de estructura esperada en el Excel:
    data = {
        "245": ["Don Quijote de la Mancha", "Cien años de soledad", "Rayuela"],
        "100": ["Miguel de Cervantes", "Gabriel García Márquez", "Julio Cortázar"],
        "260": ["Madrid, 1605", "Buenos Aires, 1967", "París, 1963"]
    }
    return pd.DataFrame(data)

def clasificar_pregunta(pregunta):
    pregunta = pregunta.upper()
    if pregunta.startswith("QUIÉN") or pregunta.startswith("QUIEN"):
        return "QUIÉN"
    elif pregunta.startswith("QUÉ") or pregunta.startswith("QUE"):
        return "QUÉ"
    elif pregunta.startswith("DÓNDE") or pregunta.startswith("DONDE"):
        return "DÓNDE"
    return None

# 3. Interfaz de Streamlit
st.title("📚 Sistema de Recuperación MARC-21")
st.write("Consulta la base de datos de la biblioteca mediante lenguaje natural.")

df = cargar_datos()
pregunta_usuario = st.text_input("Haz tu pregunta (ej: ¿Quién escribió el Quijote?):")

if pregunta_usuario:
    clase = clasificar_pregunta(pregunta_usuario)
    
    if clase:
        st.info(f"Detectada intención: **{clase}**. Buscando en etiquetas MARC: {TAXONOMIA_MARC[clase]}")
        
        # Lógica de extracción simple:
        # Buscamos palabras clave de la pregunta que no sean la interrogación
        palabras_clave = [w for w in pregunta_usuario.split() if len(w) > 3]
        termino_busqueda = palabras_clave[-1].replace("?", "") # Ej: "Quijote"

        # Buscar el término en el Título (245) para encontrar el registro
        resultado = df[df['245'].str.contains(termino_busqueda, case=False, na=False)]

        if not resultado.empty:
            for _, fila in resultado.iterrows():
                # Si la pregunta es "Quién", mostramos los campos 100, 110...
                campos_a_mostrar = TAXONOMIA_MARC[clase]
                for campo in campos_a_mostrar:
                    if campo in df.columns:
                        st.success(f"Resultado encontrado: {fila[campo]}")
        else:
            st.warning("No se encontró ese ejemplar en la biblioteca.")
    else:
        st.error("No reconozco el tipo de pregunta. Prueba con 'Quién...', 'Qué...', etc.")
