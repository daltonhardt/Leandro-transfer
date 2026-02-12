######################################################################
# Author: Dalton Hardt
# Description: Invoice/Expenses records with Google Sheets & Streamlit
# Created: 11-feb-2026
# Last Modified: 12-feb-2026
# Version: 1.0.0
######################################################################

import streamlit as st
from streamlit_option_menu import option_menu
from google.oauth2 import service_account
from googleapiclient.discovery import build
from datetime import datetime
import calendar
import json
import pandas as pd

# --- Função de login ---
def check_password():
    def password_entered():
        if st.session_state["password"] == st.secrets["senha_acesso"]["password"]:
            st.session_state["password_ok"] = True
            del st.session_state["password"]  # limpa senha da memória
        else:
            st.session_state["password_ok"] = False

    if "password_ok" not in st.session_state:
        st.text_input(
            "Digite a senha de acesso:",
            type="password",
            on_change=password_entered,
            key="password",
        )
        return False

    elif not st.session_state["password_ok"]:
        st.text_input(
            "Digite a senha de acesso:",
            type="password",
            on_change=password_entered,
            key="password",
        )
        st.error("❌ Senha incorreta")
        return False

    else:
        return True

def salvar_registro():
    dia = st.session_state.key_dia
    desc = st.session_state.key_desc
    valor = st.session_state.key_valor
    tipo = st.session_state.key_tipo

    if desc.strip() == "" or valor == 0 or tipo is None:
        st.session_state.msg_erro = "Preencha todos os campos."
        return

    dia_str = dia.strftime('%d/%m/%Y')

    if tipo == "Despesa":
        valor = -abs(valor)

    mes = dia.strftime("%b")

    registro = [dia_str, desc, valor, tipo]

    atualiza_planilha(registro, mes)

    # limpa campos do formulário
    st.session_state.key_desc = ""
    st.session_state.key_valor = 0.0
    st.session_state.key_tipo = None

    st.session_state.msg_ok = (f"Último registro: :blue-background[**{dia_str}**] :blue-background[**{desc}**] "
                               f"no valor de :blue-background[**{valor}**] "
                               f"como :blue-background[**{tipo}**]")


# Formatting datetime columns to just display the date in 'YYYY/MM/DD' format
def format_datetime_columns(dataframe):
    for col in dataframe.columns:
        if pd.api.types.is_datetime64_any_dtype(dataframe[col]):
            dataframe[col] = dataframe[col].dt.strftime('%d/%m/%y')
    return dataframe


def colored_metric(label, value, is_positive):
    # Determine color based on input
    color = "lightgreen" if is_positive else "red"

    # formata o valor para moeda em Euro
    # value_fmt = f"{value:,}"  # coloca ',' como separador de milhares
    value_fmt = value.replace(',',';')  # substitui a ',' de milhares por ';'
    value_fmt = value_fmt.replace('.',',')  # substitui o '.' do decimal por ','
    value_fmt = value_fmt.replace(';','.')  # substitui o ';' de milhares por '.'
    value_fmt = f"€ {value_fmt}"  # coloca o sinal de '€' na frente

    # Create HTML/CSS structure
    html_str = f"""
    <div style="background-color: {color}; padding: 5px; border-radius: 5px;">
        <p style="margin: 0; font-size: 14px; color: black;">{label}</p>
        <p style="margin: 0; font-size: 36px; color: black;">{value_fmt}</p>
    </div>
    """
    st.markdown(html_str, unsafe_allow_html=True)


# Function to READ/GET values from spreadsheet
def leitura_worksheet(worksheet):
    try:
        df_base = pd.DataFrame()
        for aba_mes in worksheet:
            result = sheet.values().get(spreadsheetId=SPREADSHEET_ID, range=aba_mes).execute()
            values = result.get("values", [])
            df_new = pd.DataFrame(values)  # transform all values in DataFrame
            df_new = df_new[1:]  # remove the first row from DataFrame (column names)
            df_base = pd.concat([df_base, df_new], axis=0, ignore_index=True)
        df_base.columns = ["Data", "Desc", "Valor", "Tipo"]
        df_base['Data'] = pd.to_datetime(df_base['Data'], format='%d/%m/%Y', errors="coerce")  # converte Data de object para datetime
        df_base = df_base.sort_values("Data").reset_index(drop=True)  # ordenação cronológica
        df_base['Mes'] = df_base['Data'].dt.month  # pega somente o mês da Data (em formato numérico)
        df_base['Mes_abreviado'] = df_base['Mes'].apply(lambda x: calendar.month_abbr[x])
        df_base['Valor'] = df_base['Valor'].str.replace('.','')
        df_base['Valor'] = df_base['Valor'].str.replace(',','.')
        df_base['Valor'] = pd.to_numeric(df_base['Valor'], errors='coerce')
        # df_base['Valor'] = df_base['Valor'].astype(float)  # transforma o Valor numérico em floating para poder somar depois

        return df_base

    except (RuntimeError, TypeError, NameError):
        pass

def atualiza_planilha(row, aba_mes):
    # Create new record(s) with the invoice line(s) in the spreadsheet
    sheet.values().append(spreadsheetId=SPREADSHEET_ID,
                        range=aba_mes,
                        valueInputOption="USER_ENTERED",
                        body={"values": [row]}
                        ).execute()

# --- BLOQUEIO PRINCIPAL ---
if not check_password():
    st.stop()


# --- LOCAL CONFIGURATIONS
month_option = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']

today = datetime.now()
hoje = today.strftime("%d/%m/%Y")
mes_corrente = today.strftime("%b")
# print(f'hoje = {hoje}')
# print(f'mes_corrente = {mes_corrente}')

# INICIANDO O GOOGLE SHEETS CONNECTION
# Read all GCP Credentials stored in secrets.toml file
gcp_type = st.secrets.gcp_service_account["type"]
gcp_project_id = st.secrets.gcp_service_account["project_id"]
gcp_private_key_id = st.secrets.gcp_service_account["private_key_id"]
gcp_private_key = st.secrets.gcp_service_account["private_key"].replace('\n', '\\n')
gcp_client_email = st.secrets.gcp_service_account["client_email"]
gcp_client_id = st.secrets.gcp_service_account["client_id"]
gcp_auth_uri = st.secrets.gcp_service_account["auth_uri"]
gcp_token_uri = st.secrets.gcp_service_account["token_uri"]
gcp_auth_provider_x509_cert_url = st.secrets.gcp_service_account["auth_provider_x509_cert_url"]
gcp_client_x509_cert_url = st.secrets.gcp_service_account["client_x509_cert_url"]
gcp_universe_domain = st.secrets.gcp_service_account["universe_domain"]
# Create a dictionary string
account_info_str = f'''
{{
  "type": "{gcp_type}",
  "project_id": "{gcp_project_id}",
  "private_key_id": "{gcp_private_key_id}",
  "private_key": "{gcp_private_key}",
  "client_email": "{gcp_client_email}",
  "client_id": "{gcp_client_id}",
  "auth_uri": "{gcp_auth_uri}",
  "token_uri": "{gcp_token_uri}",
  "auth_provider_x509_cert_url": "{gcp_auth_provider_x509_cert_url}",
  "client_x509_cert_url": "{gcp_client_x509_cert_url}",
  "universe_domain": "{gcp_universe_domain}"
}}
'''
# Convert to a JSON string
account_info = json.loads(account_info_str)

# Google Sheets Definitions
SCOPES = st.secrets.google_definition["SCOPES"]
SPREADSHEET_ID = st.secrets.google_definition["SPREADSHEET_ID"]

creds = service_account.Credentials.from_service_account_info(account_info, scopes=SCOPES)
# Call the Sheets API
service = build("sheets", "v4", credentials=creds)
sheet = service.spreadsheets()
# Call the Drive API
service_drive = build("drive", "v3", credentials=creds)
drive = service_drive.files()

# PANDAS PARAMETERS
# pd.set_option('display.precision', 2)
# Apply format with two decimal numbers for display only
pd.options.display.float_format = '{:,.2f}'.format
# Pandas visualization parameters
pd.set_option('display.max_columns', None)
pd.set_option('display.max_rows', None)

# INICIANDO O STREAMLIT
# st.logo(image="./images/logo.png")
st.set_page_config(page_title="Receitas/Despesas", layout="wide")
st.subheader("Receitas & Despesas")
state = st.session_state


if "visibility" not in state:
    state.visibility = "hidden"
    state.disabled = True
if "month" not in state:
    state.month = mes_corrente
if "key_valor" not in st.session_state:
    st.session_state.key_valor = 0.0
if "key_desc" not in st.session_state:
    st.session_state.key_desc = ""
if "key_tipo" not in st.session_state:
    st.session_state.key_tipo = None

# st.write(st.session_state)
# TABS
TAB_1 = 'Novo registro'
TAB_2 = 'Resultado'

tab = option_menu(
    menu_title = '',
    options = [TAB_1, TAB_2],
    icons=['bi-pencil-square', 'bar-chart'],
    orientation = 'horizontal'
)

if tab == TAB_1:
    dia = st.date_input("Data:", format="DD/MM/YYYY", key="key_dia")
    dia_str = dia.strftime('%d/%m/%Y')
    desc = st.text_input("Descrição:", key="key_desc")
    valor = st.number_input("Valor:", key="key_valor")
    tipo = st.radio("Tipo:", options=["Receita", "Despesa"], index=None, key="key_tipo")

    st.button(
        "Confirmar",
        type="primary",
        on_click=salvar_registro
    )

    # --- mensagens ---
    if "msg_erro" in st.session_state:
        st.error(st.session_state.msg_erro)
        del st.session_state.msg_erro

    if "msg_ok" in st.session_state:
        st.success(st.session_state.msg_ok)
        del st.session_state.msg_ok


if tab == TAB_2:
    meses = st.multiselect(
        "Selecione o mês ou período:",
        options=month_option,
        default=state.month,
        )
    # print(f'options: {meses}')
    # print(f'meses: {meses}')

    if len(meses) > 0:
        # Leitura dataframe
        df_original = leitura_worksheet(meses)
        # print(df_original)

        if df_original.empty:
            st.error("Não existem registros para esse período!")

        else:
            # formatação (essa função transforma a data em string
            df = format_datetime_columns(df_original)

            df_receita = df[df["Tipo"] == "Receita"].reset_index(drop=True)
            df_despesa = df[df["Tipo"] == "Despesa"].reset_index(drop=True)

            col1, col2, col3 = st.columns(3)
            with col1:
                with st.container(border=True, vertical_alignment="distribute"):
                    receita_periodo = df_receita['Valor'].sum()
                    st.metric('Receita', value=receita_periodo, format="euro")
                    # colored_metric("Receita", receita_periodo, is_positive=True)
                    # print(f'receita_periodo: {receita_periodo}')
            with col2:
                with st.container(border=True, vertical_alignment="distribute"):
                    despesa_periodo = df_despesa['Valor'].sum()
                    st.metric('Despesa', value=despesa_periodo, format="euro")
                    # colored_metric("Despesa", despesa_periodo, is_positive=True)
                    # print(f'despesa_periodo: {despesa_periodo}')
            with col3:
                with st.container(border=True, vertical_alignment="distribute"):
                    saldo_periodo = receita_periodo + despesa_periodo
                    saldo_formatado = f"{saldo_periodo:,.2f}"  # coloca ',' como separador de milhares e 2 casas decimais
                    # print(f'Saldo: {saldo_periodo}')
                    # print(f'Saldo formatado: {saldo_formatado}')
                    # st.metric('Saldo', value=saldo_periodo, format="euro", delta=saldo_periodo)
                    if saldo_periodo >= 0:
                        colored_metric("Resultado", saldo_formatado, is_positive=True)
                    else:
                        colored_metric("Resultado", saldo_formatado, is_positive=False)

            st.write("Todas Receitas e Despesas:")
            st.dataframe(df.style.format({'Valor': '€ {:.2f}'}),
                         hide_index=True, column_order=["Data", "Desc", "Valor"])

            st.write("Só Receitas:")
            st.dataframe(df_receita.style.format({'Valor': '€ {:.2f}'}),
                         hide_index=True, column_order=["Data", "Desc", "Valor"])
            st.write("Só Despesas:")
            st.dataframe(df_despesa.style.format({'Valor': '€ {:.2f}'}),
                         hide_index=True, column_order=["Data", "Desc", "Valor"])

    else:
        st.error("Selecione o mês ou o período!")

