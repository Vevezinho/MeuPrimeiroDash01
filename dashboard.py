#______________ Bibliotecas
import os
import json
import pandas as pd

# Para gerenciar o dashboard
#import dash
from dash import Dash
# Para criar componetes utilitários
from dash import dcc
# Para formatar o Layout em html
from dash import html
# Para entradas e saídas de dados nas interações
from dash.dependencies import Input, Output
# Para alguma coisa relacionada aos temas
import dash_bootstrap_components as dbc
# Tabela
from dash import dash_table
# Para pegar o id dos elementos
from dash import ctx

# Para criação de gráficos usando fórmulas de alto nível
import plotly.express as px
# Para criação de gráficos com funções mais básicas
import plotly.graph_objects as go

# Para o dropdonw interativo
from dash.exceptions import PreventUpdate


#______________ Carregando e Configurando arquivos de dados
# Arquivo de definições
dict_df_set = pd.read_excel(
    r'dados\df_set.xlsx',
    sheet_name=['df_votacao_deputados_ma','TbCv_codMunic_IbgeTse'],
    )
df_set_votacao_deputados_ma = dict_df_set['df_votacao_deputados_ma']
df_set_TbCv_codMunic_IbgeTse = dict_df_set['TbCv_codMunic_IbgeTse']
# Arquivos de dados
arq_zip = r'dados\votacao_candidato_munzona_2022_MA.zip'
arq_TbCv = r'dados\TbCv_codMunic_IbgeTse.xlsx'

# Carregando GeoJson
geo_ma_mun = json.load(open('geojson/geojs-21-mun.json','r',encoding='utf-8'))

# Carregando dados no DataFrame
df_votacao_deputados_ma = pd.read_csv(
    arq_zip,
    encoding='latin1', delimiter=';', compression='zip',
    usecols=list(
        df_set_votacao_deputados_ma['colunas'].loc[
            df_set_votacao_deputados_ma['sel']==True
            ]),
    dtype=dict(df_set_votacao_deputados_ma[['colunas','tipos']].values),
    )

# Carregando dados da Tabela de Conversão entre os Códigos Municípias IBGE e TSE
df_TbCV_codMunic = pd.read_excel(
    arq_TbCv,
    usecols=list(
        df_set_TbCv_codMunic_IbgeTse['colunas'].loc[
            df_set_TbCv_codMunic_IbgeTse['sel']==True
            ]),
    dtype=dict(df_set_TbCv_codMunic_IbgeTse[['colunas','tipos']].values),
)
# Filtrando DataFrame para apenas dados sobre o Maranhão
df_TbCV_codMunic_Ma = df_TbCV_codMunic.loc[df_TbCV_codMunic['UF_cod']=='21']
# Junção de tabelas 
df_merge = df_votacao_deputados_ma.merge(df_TbCV_codMunic_Ma, on='CD_MUNICIPIO')
# ______________ Criando arquivo base
cols = [
    'COD_MUNIC_IBGE','Nome_Município', 'DS_CARGO',
    'NM_URNA_CANDIDATO_y','SG_PARTIDO_y','NR_CANDIDATO_x','NM_URNA_CANDIDATO_x', 'SG_PARTIDO_x', 'DS_SIT_TOT_TURNO'
]
df_base = df_merge.groupby(by=cols).sum(numeric_only=True).reset_index()
# Renomeando as Colunas
df_base.rename(columns={
    'Nome_Município':'Município',
    'NM_URNA_CANDIDATO_y':'Prefeito',
    'SG_PARTIDO_y':'Partido',
    'QT_VOTOS_NOMINAIS_VALIDOS':'Votos',
    'COD_MUNIC_IBGE': 'CodIBGE',
    'DS_SIT_TOT_TURNO':'Situação',
    'NM_URNA_CANDIDATO_x':'Candidato',
},inplace=True)
# Filtro para apenas Deputados Estadual
#df_base = df_base.loc[df_base['DS_CARGO']=='Deputado Estadual']

#======================================================================================
#======================================================================================
# ______________ Variáveis para interação no DashBoard
# Número do Candidato para iniciar o mapa
num_can_inic = '20123'
# CodIBGE do Muncípio Inical
mum_inic = '2100204'
# Lista com números dos candidatos
#num_can = df_base[['NR_CANDIDATO_x','Candidato','DS_CARGO','SG_PARTIDO_x']].loc[df_base['DS_CARGO']=='Deputado Estadual'].drop_duplicates()
num_can = df_base[['NR_CANDIDATO_x','Candidato','DS_CARGO','SG_PARTIDO_x']].drop_duplicates()


def gerar_options_dropdown(coluna_value, coluna_label_01, coluna_label_02, coluna_label_03, color='#8e8e8e'):
    #https://dash.plotly.com/dash-core-components/dropdown
    lista=[]
    for index, value in coluna_value.items():
        d = dict()
        texto_dropdonw = f'{coluna_value[index]} {coluna_label_01[index]} {coluna_label_02[index]} {coluna_label_03[index]}'
        # a div foi criada para poder mudar a cor da fonte
        d['label']=html.Div([texto_dropdonw], style={'color': color})#, 'font-size': 20
        d['value']=coluna_value[index]
        # pesquisa
        d['search']=texto_dropdonw
        lista.append(d)
    return lista

#a=gerar_options_dropdown(num_can['NR_CANDIDATO_x'],num_can['Candidato'],num_can['DS_CARGO'],num_can['SG_PARTIDO_x'])
#a

# DataFrame para totalização por municípios
df_mun_cand = df_base.loc[df_base['CodIBGE']==mum_inic].sort_values('Votos', ascending=False)
nome_mun_sel = df_mun_cand['Município'].unique()[0]
df_mun_cand[['Candidato','Situação','Votos']].loc[df_mun_cand['Votos']>0]

# DataFrame para um único candidato
df_cand_mun = df_base.loc[(df_base['NR_CANDIDATO_x']==num_can_inic)&(df_base['Votos'] > 0)].sort_values('Votos', ascending=False)
# Zerei os votos para iniciar o mapa sem candidato selecionado
df_cand_mun['Votos'] = 0

# Para calcular DataFrame com o percentual de não eleitos para os municípios com votos do candidato selecionado
def calc_tabela(num_can_inic):
    # DataFrame para um único candidato
    df_cand_mun = df_base.loc[(df_base['NR_CANDIDATO_x']==num_can_inic) &(df_base['Votos'] > 0)].sort_values('Votos', ascending=False)
    #df_cand_mun = df_base.loc[df_base['NR_CANDIDATO_x']==num_can_inic].sort_values('Votos', ascending=False)

    # DataFrame com a Situação do Candidato 'DS_SIT_TOT_TURNO' totalizada em coluna por municípios
    df_munSitCand = df_base.groupby(['CodIBGE', 'Município', 'Situação']).sum(numeric_only=True).reset_index()
    df_munSitCand = df_munSitCand.pivot(index=['CodIBGE', 'Município'],columns=['Situação'],values=['Votos'])
    df_munSitCand = df_munSitCand.droplevel(0, axis=1).reset_index()
    df_munSitCand.columns.name = None

    # DataFrame Analítico Candidato - baseada em df_munSitCand e df_cand_mun
    df_AnalCand = df_cand_mun.merge(df_munSitCand)
    df_AnalCand['Total'] = df_AnalCand[['ELEITO POR MÉDIA','ELEITO POR QP','NÃO ELEITO','SUPLENTE']].sum(axis=1)
    df_AnalCand['Eleitos'] = df_AnalCand[['ELEITO POR MÉDIA','ELEITO POR QP']].sum(axis=1)
    df_AnalCand['% Eleitos'] = df_AnalCand['Eleitos']/df_AnalCand['Total']*100
    df_AnalCand['% N.E.'] = df_AnalCand['NÃO ELEITO']/df_AnalCand['Total']*100

    df = df_AnalCand[['Município','Votos','% N.E.']]
    return df.round(1)


def adicionar_coluna_ranque(df_base, num_can):
    # DataFrame com os municípios com votos do candidato
    df_cand = df_base.loc[(df_base['NR_CANDIDATO_x']==num_can)&(df_base['Votos'] > 0)].sort_values('Votos', ascending=False)
    # Cargo do candidato
    cargo_cand = df_cand['DS_CARGO'].iloc[0]
    # DataFrame do cargo do candidato selecionado
    df_cargo = df_base[df_base['DS_CARGO']==cargo_cand]
    # Criando coluna para receber o ranqueamento
    df_cand.loc[:,'Rank']=0
    # Percorrendo a lista dos municípios com votos no candidato
    for mun in df_cand['CodIBGE']:
        # DataFrame com os votos por candidatos no cargo do selecionado
        df_cargo_mun = df_cargo[(df_cargo['CodIBGE']==mun)&(df_cargo['Votos']>0)].sort_values(by='Votos', ascending=True)
        # Calculando ranque para todos os candidatos ao cargo no município
        df_cargo_mun['rank'] = (df_cargo_mun['Votos'].rank(ascending=False)).astype(int)
        # Coletando o posicionamento do selecionado no município
        rank = df_cargo_mun['rank'][df_cargo_mun['NR_CANDIDATO_x']==num_can]
        # Adicionando o posicionamento do selecionado no DataFrame com os municípios com votos do candidato
        df_cand.loc[df_cand['CodIBGE'] == mun,'Rank'] = rank
    
    #df = df_cand[['Município','Votos','Rank']]
    df = df_cand[['CodIBGE','Município','Votos','Rank']]
    return df


#======================================================================================
#======================================================================================
# Para iniciar o servidor com uma folha de tema externa
app = Dash(__name__, external_stylesheets=[dbc.themes.CYBORG])

center_lat, center_lon = -5.7, -45.2 #-5.21,-45.52
colors={
    'paper_bgcolor': '#242424'
}

#________________ Mapa
def gerar_mapa(df):
    fig = px.choropleth_mapbox( 
        df, 
        center={'lat':center_lat, 'lon':center_lon}, zoom=5.4,      
        locations='CodIBGE', 
        color='Votos',
        geojson=geo_ma_mun, featureidkey='properties.id',  
        color_continuous_scale='Redor', opacity=0.4,
        hover_data={        
            'Município':True,
            'Prefeito':True,
            'Partido':True,
            'Votos':True,
            'CodIBGE': False,
        },
    )

    fig.update_layout(
        paper_bgcolor=colors['paper_bgcolor'],
        autosize=True,
        margin=go.layout.Margin(l=0, r=0, t=0, b=0),
        showlegend=True,
        mapbox_style='carto-darkmatter'
    )
    return fig


#======================================================================================
#======================================================================================
# ______________Layout

app.layout = dbc.Container(
    dbc.Row([
        dbc.Col([
                html.Div([
                    html.Img(id='logo', src=app.get_asset_url('logo_tranparente.png'), height=60),# 
                    html.H6('Além da Análise de Dados'),# 'Localidade:'
                    #dbc.Button('Maranhão', color='primary', id='location-button', size='lg',style={'margin-top':'15px'}),
                    ##################################################################################
                    dbc.Alert(id='tbl_out2', style={'display':'none'})
                ], style={'textAlign':'center'}), 
            html.P( style={'margin-top':'15px', 'color':'white'}),#'Informe o número do Deputado Estadual que deseja obter informações:'
            dbc.Row([
                #html.H6('Texto'),
                dcc.Dropdown(
                    id='dropdown-dep-nun',
                    optionHeight=50,
                    placeholder="Selecione um candidato...",
                    options=gerar_options_dropdown(num_can['NR_CANDIDATO_x'],num_can['Candidato'],num_can['DS_CARGO'],num_can['SG_PARTIDO_x']),
                    #value=num_can_inic,
                    clearable=True,
                    style={'margin-top':'0px'}#, 'color':'#EAEAEA'
                )
            ]),
            dbc.Row([
                dbc.Col([
                    dbc.Card([
                        dbc.CardBody([
                            html.Span('Candidato'),
                            html.H5(id='nome-candidato-text', style={'color':'#EAEAEA'})
                        ])
                    ], style={'margin-top':'15px'})
                ])
            ]),
            dbc.Row([
                dbc.Col([
                    dbc.Card([
                        dbc.CardBody([
                            html.Span('Votos'),
                            html.H6(id='total-votos-text', style={'color':'#EAEAEA'})
                        ])
                    ], color='light', outline=True, style={'margin-top':'15px', 'textAlign':'center'})
                ]),
                dbc.Col([
                    dbc.Card([
                        dbc.CardBody([
                            html.Span('Municípios'),
                            html.H6(id='total-mun-text', style={'color':'#EAEAEA'})
                        ])
                    ], color='light', outline=True, style={'margin-top':'15px', 'textAlign':'center'})
                ])
            ]),
            dbc.Row([
                dbc.Col([
                    dbc.Card([
                        dbc.CardBody([
                            html.Span('Status'),
                            html.H5(id='status-text', style={'color':'#EAEAEA'})
                        ])
                    ], color='light', outline=True, style={'margin-top':'15px'})
                ])
            ]),
            dbc.Row([
                dbc.Col([
                    #html.Span('Clique no mapa para vizualizar a votação no município.'), #, style={'fontWeight':'bold'}
                    dcc.Tab(id='tab-anal-cand', style={'height':'100vh'})], style={'textAlign':'center'}),
            ],style={'margin-top':'15px'},)        
        ], md=4, style={'padding':'25px'}),
        dbc.Col([
            #dbc.Row(id='linha_mapa'), #antes recebia o loading da função
            dbc.Row(
                dcc.Loading(id='loading-1', type='default', children=[],)
            ),
            dbc.Row([
                dbc.Col([
                    html.Div([
                        dbc.Alert(id='tbl_out', style={'display':'none'}),
                        dbc.Col(id='card_municipio'),
                        #dbc.Row(id='card_municipio'),
                        dbc.Row([
                            dbc.Col(id='card_prefeito'),
                            dbc.Col(id='card_partido'),
                        ]),dbc.Row([
                            dbc.Col(id='cardT_votos_mun_cand'), 
                            dbc.Col(id='card_votos_mun_cand'), 
                        ]),
                        dbc.Row([
                            dbc.Col(id='card_cargo'), 
                            dbc.Col(id='card_votos'), 
                        ]),
                        dbc.Row([
                            dbc.Col(id='cardT_repre_mun_cand'),
                            dbc.Col(id='card_repre_mun_cand'),
                        ]),
                        dbc.Row([
                            dbc.Col(id='cardT_repre_cand_mun'),
                            dbc.Col(id='card_repre_cand_mun'),
                        ])
                    ], style={'height':'300px', 'textAlign':'center'})#'backgroundColor':'white',
                ]),#id='coluna_cards'
                dbc.Col([dcc.Tab(id='tab-anal-mun', style={'height':'100vh'}),], md=6),
            ], style={'margin-top':'15px'})
            ], md=8)
    ], class_name='g-0')
, fluid=True)

#======================================================================================
#======================================================================================
# ______________Interactivity

# Tabela 
@app.callback(
    Output('tab-anal-cand','children'),
    Input('dropdown-dep-nun','value'),
)

def imprimir_tabela_candidato(value):
    # Para gerar a tabela
    if value==None:
        return None
    #df = calc_tabela(value)
    df = adicionar_coluna_ranque(df_base, value)    
    tabela = dash_table.DataTable(
        df.to_dict('records'), [{"name": i, "id": i} for i in df.columns],
        id='tbl',
        #style_cell={'textAlign': 'right'},
        #locale_format={'decimal':',', 'group':','},
        fixed_rows={'headers':True, 'data':0},
        page_size=11,
        sort_action="native",
        sort_mode="multi",
        hidden_columns=['CodIBGE'],
        style_header={'backgroundColor': '#282828', 'fontWeight': 'bold', 'textAlign':'center', 'border':'0.5px black'},
        style_data={'backgroundColor': '#282828', 'color':'#EAEAEA','border':'0.5px solid black'},
        style_as_list_view=True,
        style_cell_conditional=[
            {'if': {'column_id': 'CodIBGE'},'textAlign': 'left'},
            {'if': {'column_id': 'Município'},'textAlign': 'left'},
        ],
        )
    return tabela

# Cartões
@app.callback(
    [
        Output('nome-candidato-text','children'),
        Output('total-votos-text','children'),
        Output('total-mun-text','children'),
        Output('status-text','children')
    ],
    [Input('dropdown-dep-nun','value')]
)
def cartoes_interacao(value):
    df_cand_mun_ =  df_base.loc[df_base['NR_CANDIDATO_x']==value].sort_values('CodIBGE', ascending=True)
    nome_candidato = df_cand_mun_['Candidato'].unique()[0]
    total_votos = f"{df_cand_mun_['Votos'].sum():,}".replace(',','.')
    num_mun_cand = len(df_cand_mun_[df_cand_mun_['Votos']>0])
    status = df_cand_mun_['Situação'].unique()[0]
    return (nome_candidato, total_votos, num_mun_cand, status)

# Cartões da segunda parte
# cartão município
@app.callback(
    [Output('card_municipio','children'),],[Input('choropleth-map','clickData'),Input('dropdown-dep-nun', 'value'),Input('tbl_out','children'),]
)
def imprimir_coluna_cartoes(click_data, value, children):
    if value==None:
        return None
    changed_id = [p['prop_id'] for p in ctx.triggered][0]
    if (click_data is not None and changed_id != 'location-button.n_clicks') or (children is not None and changed_id == 'tbl_out.children'):
        if changed_id == 'choropleth-map.clickData':
            localidade = click_data['points'][0]['location']
        if changed_id == 'tbl_out.children':
            localidade = children

        df = df_base[df_base['CodIBGE']==localidade]
        municipio = df['Município'].drop_duplicates().values[0]

    return [
        dbc.Card([
                dbc.CardBody([
                    #html.Span(''),
                    html.Span(municipio, style={'color':'#EAEAEA', 'textAlign':'center',})
                ])
            ], style={'margin-top':'0px'})
    ]
# cartão prefeito
@app.callback(
    [Output('card_prefeito','children'),],[Input('choropleth-map','clickData'),Input('tbl_out','children'),]
)
def imprimir_coluna_cartoes(click_data, children):
    changed_id = [p['prop_id'] for p in ctx.triggered][0]
    if (click_data is not None and changed_id != 'location-button.n_clicks') or (children is not None and changed_id == 'tbl_out.children'):
        if changed_id == 'choropleth-map.clickData':
            localidade = click_data['points'][0]['location']
        if changed_id == 'tbl_out.children':
            localidade = children

        df = df_base[df_base['CodIBGE']==localidade]
        prefeito = df['Prefeito'].drop_duplicates().values[0]

    return [
        dbc.Card([
                dbc.CardBody([
                    html.Span(prefeito, style={'color':'#EAEAEA'})
                ])
            ], style={'margin-top':'5px', 'textAlign':'center'})
    ]
# cartão partido
@app.callback(
    [Output('card_partido','children'),],[Input('choropleth-map','clickData'), Input('tbl_out','children'),]
)
def imprimir_coluna_cartoes(click_data, children):
    changed_id = [p['prop_id'] for p in ctx.triggered][0]
    if (click_data is not None and changed_id != 'location-button.n_clicks') or (children is not None and changed_id == 'tbl_out.children'):
        if changed_id == 'choropleth-map.clickData':
            localidade = click_data['points'][0]['location']
        if changed_id == 'tbl_out.children':
            localidade = children

        df = df_base[df_base['CodIBGE']==localidade]
        partido = df['Partido'].drop_duplicates().values[0]   

    return [
        dbc.Card([
                dbc.CardBody([
                    html.Span(partido, style={'color':'#EAEAEA'})# , 'textAlign':'center'
                ])
            ], style={'margin-top':'5px'})
    ]
# cartão cargo
@app.callback(
    [
        Output('cardT_votos_mun_cand','children'),
        Output('card_cargo','children'),
        Output('cardT_repre_mun_cand','children'),
        Output('cardT_repre_cand_mun','children'),
        
    ],[
        Input('choropleth-map','clickData'),
        Input('dropdown-dep-nun', 'value'),
        Input('tbl_out','children'),
    ]
)
def imprimir_coluna_cartoes(click_data, value, children):
    if value==None:
        return None
    changed_id = [p['prop_id'] for p in ctx.triggered][0]
    if (click_data is not None and changed_id != 'location-button.n_clicks') or (children is not None and changed_id == 'tbl_out.children'):
        if changed_id == 'choropleth-map.clickData':
            localidade = click_data['points'][0]['location']
        if changed_id == 'tbl_out.children':
            localidade = children

        df = df_base[df_base['CodIBGE']==localidade]

        cargo = df['DS_CARGO'].loc[df['NR_CANDIDATO_x']==value].drop_duplicates().values[0]

        cardT_votos_mun_cand = f"Votos no município"
        card_cargo = f"a {cargo}"
        card_cargo = f"Total ao Cargo"
        cardT_repre_mun_cand = f"Repr. Municipal"
        cardT_repre_cand_mun = f"Repr. Candidato"

        def gerar_cardT(texto):
            cardT = dbc.Card([
                dbc.CardBody([
                    html.P(f"{texto}", style={'color':'#EAEAEA'})
                ])
            ], style={'margin-top':'5px', 'fonte-size':'smaller'})
            return cardT

    return (
        [gerar_cardT(cardT_votos_mun_cand)],
        [gerar_cardT(card_cargo)],
        [gerar_cardT(cardT_repre_mun_cand)],
        [gerar_cardT(cardT_repre_cand_mun)],
    )
# cartão votos
@app.callback(
    [
        Output('card_votos_mun_cand','children'),
        Output('card_votos','children'),
        Output('card_repre_mun_cand','children'),
        Output('card_repre_cand_mun','children'),
        Output('tbl_out2','children'),
    ],[
        Input('choropleth-map','clickData'),
        Input('dropdown-dep-nun', 'value'),
        Input('tbl_out','children'),
    ]
)
def imprimir_coluna_cartoes(click_data, value, children):
    if value==None:
        return None
    changed_id = [p['prop_id'] for p in ctx.triggered][0]
    if (click_data is not None and changed_id != 'location-button.n_clicks') or (children is not None and changed_id == 'tbl_out.children'):
        if changed_id == 'choropleth-map.clickData':
            localidade = click_data['points'][0]['location']
        if changed_id == 'tbl_out.children':
            localidade = children

        df_mun = df_base[df_base['CodIBGE']==localidade]
        df_mun_cand = df_mun[df_mun['NR_CANDIDATO_x']==value]
        votos_mun_cand = df_mun_cand['Votos'].sum()

        cargo = df_mun_cand['DS_CARGO'].drop_duplicates().values[0]
        #votos = f"{df['Votos'].loc[df['DS_CARGO']==cargo].sum():,}".replace(',','.')  
        votos_cargo = df_mun['Votos'].loc[df_mun['DS_CARGO']==cargo].sum()#.replace(',','.')
        votos_mun = df_mun['Votos'].sum()

        df_cand =  df_base.loc[df_base['NR_CANDIDATO_x']==value].sort_values('CodIBGE', ascending=True)
        votos_cand = df_cand['Votos'].sum()

        card_repre_mun_cand = (votos_mun_cand/votos_cand)*100
        card_repre_cand_mun = (votos_mun_cand/votos_cargo)*100

        card_votos_mun_cand = f'{votos_mun_cand:,}'.replace(',','.')
        card_votos_cargo = f'{votos_cargo:,}'.replace(',','.')
        card_repre_mun_cand= f"{card_repre_mun_cand:,.2f}%".replace(',','_').replace('.',',').replace('_','.')
        card_repre_cand_mun= f"{card_repre_cand_mun:,.2f}%".replace(',','_').replace('.',',').replace('_','.')
        
        def gerar_cardN(valor):
            cardN = dbc.Card([
                dbc.CardBody([
                    html.P(f"{valor}", style={'color':'#EAEAEA'})
                ])
            ], style={'margin-top':'5px'})
            return cardN

    return (
        [gerar_cardN(card_votos_mun_cand)],
        [gerar_cardN(card_votos_cargo)],
        [gerar_cardN(card_repre_mun_cand)],
        [gerar_cardN(card_repre_cand_mun)],
        [str([children, changed_id, click_data])],
    )

# Mapa
@app.callback(
    Output('loading-1','children'),# 
    [Input('dropdown-dep-nun', 'value')]
)
def mapa_interacao(value):
    if value == None:
        raise PreventUpdate
    else:
        df_cand_mun_ =  df_base.loc[df_base['NR_CANDIDATO_x']==value].sort_values('CodIBGE', ascending=True)
        fig = gerar_mapa(df_cand_mun_)

        linha_mapa = [
            dcc.Graph(id='choropleth-map', style={'height':'60vh',},figure=fig,)
        ]
    return linha_mapa

#Tabela Analítica do Município - por localização
@app.callback(
    Output('tab-anal-mun', 'children'),
    [
        Input('dropdown-dep-nun','value'),
        Input('choropleth-map','clickData'),
        Input('tbl_out','children'),
    ]
)

def updat_location(value, click_data, children):
    # Para gerar a tabela
    if value==None:
        return None
    changed_id = [p['prop_id'] for p in ctx.triggered][0]
    if (click_data is not None and changed_id != 'location-button.n_clicks') or (children is not None and changed_id == 'tbl_out.children'):
        if changed_id == 'choropleth-map.clickData':
            localidade = click_data['points'][0]['location']
        if changed_id == 'tbl_out.children':
            localidade = children

        cargo = df_base['DS_CARGO'].loc[df_base['NR_CANDIDATO_x']==value].drop_duplicates().values[0]
        df_mun_cand = df_base.loc[(df_base['CodIBGE']==localidade)&(df_base['DS_CARGO']==cargo)].sort_values('Votos', ascending=False)
        df = df_mun_cand[['Candidato','Situação','Votos']].loc[df_mun_cand['Votos']>0]

        tabela = dash_table.DataTable(
            df.to_dict('records'), [{"name": i, "id": i} for i in df.columns],
            #fixed_rows={'headers':True, 'data':0},
            page_size=9,
            style_header={'backgroundColor': '#282828', 'fontWeight': 'bold', 'textAlign':'center', 'border':'0.5px black'},
            style_data={'backgroundColor': '#282828', 'color':'#EAEAEA','border':'0.5px solid black'},
            style_as_list_view=True,
            style_cell_conditional=[
                {'if': {'column_id': 'Candidato'},'textAlign': 'left'},
                {'if': {'column_id': 'Situação'},'textAlign': 'center'}
            ],
            )
        return tabela
    else:
        return 'Clique no mapa ou na tabela para detalhar informações sobre o município e a votação ao cargo.'

"""
@app.callback(Output('tbl_out', 'children'), Input('tbl', 'active_cell'))
def update_graphs(active_cell):
    return str(active_cell)# if active_cell else "Click the table"

"""

@app.callback(
    Output('tbl_out','children'),
    Input('tbl','data'),
    Input('tbl','active_cell'),
)
def update_alerta(data, active_cell):
    #if active_cell == None:
        #return 'Clique na tabela'
    lista_dados_tabela = data
    dicionario_celula_ativa = active_cell
    linha = dicionario_celula_ativa['row']
    #coluna = dicionario_celula_ativa['column_id'] #Para nome da coluna ativa.
    #valor = lista_dados_tabela[linha][coluna] #Para valor da coluna ativa.
    valor = lista_dados_tabela[linha]['CodIBGE'] #Para valor da coluna selecionada.
    return valor


if __name__=='__main__':
    app.run_server(debug=False)