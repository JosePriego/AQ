import streamlit as st
import pandas as pd

@st.cache_data
def cargar_datos():
    try:
        # Cargamos el Excel y nos aseguramos de que los nombres de columnas sean texto
        df = pd.read_excel("biblioteca.xlsx", dtype=str)
        # Limpiamos espacios en blanco en los nombres de las columnas por si acaso
        df.columns = [str(c).strip() for c in df.columns]
        return df
    except Exception as e:
        st.error(f"Error: No se pudo leer 'biblioteca.xlsx'. {e}")
        return pd.DataFrame()

def extraer_entidad(pregunta):
    # Quitamos ruidos e interrogaciones
    ruido = ["QUÉ", "QUE", "QUIÉN", "QUIEN", "DÓNDE", "DONDE", "ESCRIBIÓ", "ESCRIBIO", "DE", "EL", "LA"]
    palabras = pregunta.replace("?", "").replace("¿", "").split()
    # Filtramos comparando en mayúsculas pero manteniendo el formato original para la búsqueda
    limpio = [p for p in palabras if p.upper() not in ruido]
    return " ".join(limpio).strip()

# --- Interfaz ---
st.title("📚 Buscador Bibliotecario MARC-21")
df = cargar_datos()

if not df.empty:
    pregunta_usuario = st.text_input("Tu pregunta:")

    if pregunta_usuario:
        pregunta_up = pregunta_usuario.upper()
        entidad = extraer_entidad(pregunta_usuario)
        
        # Lógica de asignación de campos según tu taxonomía
        if "QUIÉN" in pregunta_up or "QUIEN" in pregunta_up:
            col_busqueda, col_respuesta = "245", "100"
        elif "QUÉ" in pregunta_up or "QUE" in pregunta_up:
            col_busqueda, col_respuesta = "100", "245"
        else:
            col_busqueda, col_respuesta = "245", "260"

        # LA CLAVE: Búsqueda insensible a mayúsculas
        if col_busqueda in df.columns:
            # case=False ignora mayúsculas/minúsculas automáticamente
            mask = df[col_busqueda].str.contains(entidad, case=False, na=False)
            resultados = df[mask]

            if not resultados.empty:
                st.info(f"Resultados para: {entidad}")
                for res in resultados[col_respuesta].unique():
                    st.success(f"📌 {res}")
            else:
                st.warning(f"No encontré nada para '{entidad}' en el campo {col_busqueda}")
        else:
            st.error(f"La columna {col_busqueda} no existe en tu Excel.")
