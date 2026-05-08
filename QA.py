import streamlit as st
import pandas as pd
from difflib import get_close_matches

# Configuración de página para que se vea más profesional
st.set_page_config(page_title="Biblioteca Inteligente MARC21", page_icon="📖")

@st.cache_data
def cargar_datos():
    try:
        # Cargamos el Excel. Asegúrate de que el nombre sea exacto.
        df = pd.read_excel("biblioteca.xlsx", dtype=str)
        # Limpiamos posibles espacios en los nombres de las columnas
        df.columns = [str(c).strip() for c in df.columns]
        return df
    except Exception as e:
        st.error(f"No se pudo cargar 'biblioteca.xlsx'. Error: {e}")
        return None

def extraer_entidad(pregunta):
    ruido = ["QUÉ", "QUE", "QUIÉN", "QUIEN", "DÓNDE", "DONDE", "CUÁNDO", "CUANDO", "ESCRIBIÓ", "ESCRIBIO", "DE", "EL", "LA", "EL"]
    palabras = pregunta.replace("?", "").replace("¿", "").split()
    limpio = [p for p in palabras if p.upper() not in ruido]
    return " ".join(limpio).strip()

def mostrar_resultado_formateado(df_resultados, columna_objetivo):
    """Función auxiliar para mostrar 'Anónimo' si no hay datos"""
    for res in df_resultados[columna_objetivo].unique():
        # Verificamos si es nulo, nan o vacío
        if pd.isna(res) or str(res).strip().lower() in ["nan", ""]:
            if columna_objetivo == "100":
                st.success("✅ Autor: **Anónimo**")
            else:
                st.warning(f"⚠️ El campo {columna_objetivo} no tiene información registrada.")
        else:
            st.success(f"✅ Encontrado: **{res}**")

# --- INTERFAZ ---
st.title("📚 Sistema de Recuperación MARC-21")
df = cargar_datos()

if df is not None:
    pregunta_usuario = st.text_input("Haz tu pregunta a la biblioteca:")

    if pregunta_usuario:
        entidad = extraer_entidad(pregunta_usuario)
        pregunta_up = pregunta_usuario.upper()
        
        if not entidad:
            st.warning("Por favor, introduce el nombre de un autor o el título de un libro.")
        else:
            # Lógica de asignación según taxonomía
            if any(w in pregunta_up for w in ["QUIÉN", "QUIEN"]):
                col_busqueda, col_res = "245", "100"
            elif any(w in pregunta_up for w in ["QUÉ", "QUE"]):
                col_busqueda, col_res = "100", "245"
            else:
                # Por defecto si no detecta, busca por título
                col_busqueda, col_res = "245", "260"

            # 1. Búsqueda Directa (insensible a mayúsculas)
            mask = df[col_busqueda].str.contains(entidad, case=False, na=False)
            resultados = df[mask]

            if not resultados.empty:
                st.write(f"Resultados encontrados para '{entidad}':")
                mostrar_resultado_formateado(resultados, col_res)
            
            # 2. SISTEMA DE SUGERENCIAS (Si falla la directa o para ayudar)
            else:
                st.info("No hay coincidencias exactas. Buscando sugerencias...")
                posibilidades = df[col_busqueda].dropna().unique().tolist()
                sugerencias = get_close_matches(entidad, posibilidades, n=3, cutoff=0.4)
                
                if sugerencias:
                    st.write("¿Quizás buscabas uno de estos títulos/autores?")
                    cols = st.columns(len(sugerencias))
                    for i, sug in enumerate(sugerencias):
                        if cols[i].button(sug):
                            # Al pulsar la sugerencia, aplicamos la misma lógica de Anónimo
                            res_sugerencia = df[df[col_busqueda] == sug]
                            mostrar_resultado_formateado(res_sugerencia, col_res)
                else:
                    st.error("No se encontraron registros ni sugerencias para esa búsqueda.")
