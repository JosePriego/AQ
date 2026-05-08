import requests
import pandas as pd
import xml.etree.ElementTree as ET
import time

# Configuración
BASE_URL = "https://cbua-uco.alma.exlibrisgroup.com/view/sru/34CBUA_UCO"
MAX_RECORDS = 1000
STEP = 100  # Alma suele limitar bloques de 100 en SRU
NAMESPACE = {'marc': 'http://www.loc.gov/MARC21/slim', 'srw': 'http://www.loc.gov/zing/srw/'}

def get_field(record, tag, subfield=None):
    xpath = f".//marc:datafield[@tag='{tag}']"
    if subfield:
        xpath += f"/marc:subfield[@code='{subfield}']"
    else:
        xpath = f".//marc:controlfield[@tag='{tag}']"
    
    element = record.find(xpath, NAMESPACE)
    return element.text if element is not None else ""

data = []

print(f"Iniciando descarga de {MAX_RECORDS} registros...")

for start in range(1, MAX_RECORDS + 1, STEP):
    params = {
        'version': '1.2',
        'operation': 'searchRetrieve',
        'query': 'alma.all_for_ui=all',
        'maximumRecords': STEP,
        'startRecord': start
    }
    
    response = requests.get(BASE_URL, params=params)
    root = ET.fromstring(response.content)
    records = root.findall(".//marc:record", NAMESPACE)
    
    for rec in records:
        data.append({
            'Control (001)': get_field(rec, '001'),
            'ISBN (020$a)': get_field(rec, '020', 'a'),
            'Autor (100$a)': get_field(rec, '100', 'a'),
            'Título (245$a)': get_field(rec, '245', 'a'),
            'Editorial (260$b)': get_field(rec, '260', 'b'),
            'Fecha (260$c)': get_field(rec, '260', 'c'),
            'Materia (650$a)': get_field(rec, '650', 'a')
        })
    
    print(f"Progreso: {len(data)} registros procesados...")
    time.sleep(1) # Respeto al servidor

# Guardar a Excel
df = pd.DataFrame(data)
df.to_excel("Catalogacion_UCO_1000.xlsx", index=False)
print("¡Archivo 'Catalogacion_UCO_1000.xlsx' creado con éxito!")
