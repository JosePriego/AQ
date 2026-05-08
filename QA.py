import streamlit as st
import pandas as pd
from difflib import get_close_matches

@st.cache_data
def cargar_datos():
    try:
        # Cargamos el archivo real que subiste
        df = pd.read_excel("biblioteca.xlsx", dtype=str)
        df.columns = [str(c).strip() for c in df.columns]
        return df
    except Exception as e:
        st.error(f"Error: {e}")
        return None

def extraer_entidad(pregunta):
    ruido = ["QUÉ", "QUE", "QUIÉN", "QUIEN", "DÓNDE", "DONDE", "ESCRIBIÓ", "ESCRIBIO", "DE", "EL", "LA", "ESCRIBE"]
    palabras = pregunta.replace("?", "").replace("¿", "").split()
    limpio = [p for p in palabras if p.upper() not in ruido]
    return " ".join(limpio).strip()

st.title("📚 Asistente de Biblioteca MARC-21")
df = cargar_datos()

if df is not None:
    pregunta_usuario = st.text_input("Consulta (ej: ¿Qué escribió Jeremy?):")

    if pregunta_usuario:
        entidad = extraer_entidad(pregunta_usuario)
        pregunta_up = pregunta_usuario.upper()
        
        # Lógica de campos
        if any(w in pregunta_up for w in ["QUIÉN", "QUIEN"]):
            col_busqueda, col_res = "245", "100"
        elif any(w in pregunta_up for w in ["QUÉ", "QUE"]):
            col_busqueda, col_res = "100", "245"
        else:
            col_busqueda, col_res = "245", "260"

        # 1. Búsqueda Directa
        mask = df[col_busqueda].str.contains(entidad, case=False, na=False)
        resultados = df[mask]

        # Mostramos resultados directos si existen y no son nulos
        encontrado_valido = False
        if not resultados.empty:
            for res in resultados[col_res].dropna().unique():
                if str(res).lower() != "nan":
                    st.success(f"✅ Encontrado: {res}")
                    encontrado_valido = True
        
        # 2. SISTEMA DE SUGERENCIAS (Se activa si no hay éxito o como ayuda extra)
        if not encontrado_valido:
            st.info(f"No hay coincidencias exactas para '{entidad}'. Buscando sugerencias...")
            
            # Obtenemos todos los valores de la columna (ej: todos los autores)
            posibilidades = df[col_busqueda].dropna().unique().tolist()
            
            # Bajamos el cutoff a 0.4 para ser más flexibles con nombres mal escritos
            sugerencias = get_close_matches(entidad, posibilidades, n=5, cutoff=0.4)
            
            if sugerencias:
                st.write("¿Quizás quisiste decir alguno de estos?")
                cols = st.columns(len(sugerencias)) # Botones en paralelo
                for i, sug in enumerate(sugerencias):
                    if cols[i].button(sug):
                        # Al clicar, mostramos lo que corresponde a esa sugerencia
                        final = df[df[col_busqueda] == sug]
                        for r in final[col_res].dropna().unique():
                            st.success(f"📖 {r}")
            else:
                st.error("No he podido encontrar nada similar en la base de datos.")
