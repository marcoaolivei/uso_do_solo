import streamlit as st
import pandas as pd
import geemap
import folium
import geemap.foliumap as geemap
import ee 
import json
import plotly.express as px

st.set_page_config(layout="wide")

# Inicialização do GEE - executar no terminal "earthengine authenticate --force"
ee.Initialize(project='ee-marco-fertihedge')
m = geemap.Map(center=(-12, -55), zoom=6)

## Título do app
st.title('App - MapBiomas')
st.write('Este aplicativo permite a visualização interativa da classificação de uso do solo no Brasil, utilizando dados da coleção 9 do projeto do MapBiomas.  COm uma série histórica de 1985 a 2023, o aplicativo oferece a possibilidade de selecionar o ano e visualizar o uso do solo rempapeado em seus classes principais. **Fonte de dados**: [MapBiomas](https://mapbiomas.org).')

## Análise de sensoriamento remoto
mapbiomas_image = ee.Image('projects/mapbiomas-public/assets/brazil/lulc/collection9/mapbiomas_collection90_integration_v1')

# Códigos originais e classes remapeadas conforme a legenda fornecida
codes = [
    1, 3, 4, 5, 6, 49,          # Floresta e subcategorias
    10, 11, 12, 32, 29, 50,     # Vegetação Herbácea e Arbustiva e subcategorias
    14, 15, 18, 19, 39, 20, 40, 62, 41, 36, 46, 47, 35, 48, 9, 21,  # Agropecuária e subcategorias
    22, 23, 24, 30, 25,         # Área não Vegetada e subcategorias
    26, 33, 31,                 # Corpo D'água e subcategorias
    27                          # Não Observado
]

new_classes = [
    1, 1, 1, 1, 1, 1,           # Floresta e subcategorias
    2, 2, 2, 2, 2, 2,           # Vegetação Herbácea e Arbustiva e subcategorias
    3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, # Agropecuária e subcategorias
    19, 19, 19, 19, 19,              # Área não Vegetada e subcategorias
    20, 20, 20,                    # Corpo D'água e subcategorias
    21                           # Não Observado
]

# Dicionário para mapeamento de nomes das classes
class_names = {
    1: "Floresta",
    2: "Vegetação Herbácea e Arbustiva",
    3: "Agropecuária",
    4: "Pastagem",
    5: "Agricultura Anual",
    6: "Lavoura temporária",
    7: "Soja",
    8: "Cana",
    9: "Arroz",
    10: "Algodão",
    11: "Outras lavouras temporárias",
    12: "Lavoura Perene",
    13: "Café",
    14: "Citrus",
    15: "Dendê",
    16: "Outras lavouras perenes",
    17: "Silvicultura",
    18: "Mosaico de usos",
    19: "Área não Vegetada",
    20: "Corpo D'água",
    21: "Não Observado"
}

# Palette de cores para as classes remapeadas
palette = [
    "#1f8d49",  # 1. Floresta
    "#ad975a",  # 2. Vegetação Herbácea e Arbustiva
    "#ffefc3", # 3. Agropecuária
    "#808080", # 4. Pastagem
    "#E974ED", # 5. Agricultura Anual
    "#C27BA0", # 6. Lavoura temporária
    "#00ff00", # 7. Soja
    "#FFD700", # 8. Cana
    "#c71585", # 9. Arroz
    "#4682B4", # 10. Algodão
    "#f54ca9", # 11. Outras lavouras temporárias
    "#d082de", # 12. Lavoura Perene
    "#CD5C5C", # 13. Café
    "#9932cc", # 14. Citrus
    "#9065d0", # 15. Dendê
    "#e6ccff", # 16. Outras lavouras perenes
    "#7a5900", # 17. Silvicultura
    "#ffefc3", # 18. Mosaico de usos
    "#d4271e", # 19. Área não Vegetada
    "#0000FF", # 20. Corpo D'água
    "#ffffff"  # 21. Não Observado
]

# Aplicar remapeamento para cada ano e construir uma nova imagem com todas as bandas remapeadas
remapped_bands = []
for year in range(1985, 2024):
    original_band = f"classification_{year}"
    remapped_band = mapbiomas_image.select(original_band).remap(codes, new_classes).rename(original_band)
    remapped_bands.append(remapped_band)

# Combinar as bandas remapeadas em uma única imagem
remapped_image = ee.Image.cat(remapped_bands)

# Seletor de ano com opção múltipla, começando com o ano de 2023
years = list(range(1985, 2024))
selected_years = st.multiselect("Selecione o(s) ano(s)", years, default=[2023])

# Expander para inserir a área de estudo pelo usuário (em formato GeoJSON)
with st.expander("Defina a área de estudo (opcional)"):
    geometry_input = st.text_area(
        "Insira as coordenadas da área de estudo em formato GeoJSON. Utilize o mapa abaixo e as ferramentas de geometria para selecionar sua área de esutdo. Depois, clique sobre a área de interesse e selecione a feature.",
        ""
    )

# Verificar se a área foi inserida corretamente e criar a geometria
geometry = None
if geometry_input:
    try:
        geometry = ee.Geometry(json.loads(geometry_input)["geometry"])
    except json.JSONDecodeError as e:
        st.error(f"Erro no formato de coordenadas: {str(e)}. Verifique o JSON inserido.")

# Se houver uma geometria, aplicar o recorte e centralizar o mapa na área de estudo
if geometry:
    # Exibir a área de estudo no mapa
    study_area = ee.FeatureCollection([ee.Feature(geometry)])
    m.centerObject(study_area, zoom=8)
    m.addLayer(study_area, {"color": "red"}, "Área de Estudo")

    # Recortar a imagem remapeada pela geometria da área de estudo
    remapped_image = remapped_image.clip(geometry)

# Adicionar as bandas remapeadas selecionadas ao mapa
for year in selected_years:
    selected_band = f"classification_{year}"
    m.addLayer(remapped_image.select(selected_band), {'palette': palette, 'min': 1, 'max': 21}, f"Classificação Remapeada {year}")

# Exibir o mapa no Streamlit
m.to_streamlit(height=600)

# Função para calcular a área por classe
if geometry:
    st.subheader("Estatísticas de Área por Classe")
    areas = []
    for year in selected_years:
        band = remapped_image.select(f"classification_{year}")
        for class_value in range(1, 22):  # Classes de 1 a 21
            class_area = band.eq(class_value).multiply(ee.Image.pixelArea()).reduceRegion(
                reducer=ee.Reducer.sum(),
                geometry=geometry,
                scale=30,
                maxPixels=1e13
            ).getInfo()
            area_km2 = class_area.get(f"classification_{year}", 0) / 1e6  # Convertendo para km²
            areas.append({"Ano": year, "Classe": class_value, "Nome da Classe": class_names[class_value], "Área (km²)": area_km2})
    
    # Convertendo os dados de área para um único DataFrame
    df = pd.DataFrame(areas)

    # Layout de colunas
    col1, col2 = st.columns(2)

    # Exibir DataFrame e gráfico lado a lado
    with col1:
        st.dataframe(df)

    # Exibir gráfico apenas se houver mais de um ano selecionado
    if len(selected_years) > 1:
        with col2:
            # Criando o gráfico de área com Plotly
            fig = px.area(
                df,
                x="Ano",
                y="Área (km²)",
                color="Nome da Classe",
                title="Evolução da Área por Classe ao Longo do Tempo",
                color_discrete_sequence=palette
            )
            st.plotly_chart(fig, use_container_width=True)
else:
    st.info("Nenhuma área de estudo definida. As estatísticas de área por classe não serão exibidas.")


