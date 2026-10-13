from datetime import date, datetime
from decimal import Decimal

import pandas as pd
import streamlit as st

from database.conexao import conectar
from services.comissoes import ErroValidacaoComissoes, processar_texto_json
from services.estoque import (
    TIPOS_MOVIMENTACAO,
    ErroEstoque,
    listar_movimentacoes,
    listar_produtos,
    registrar_movimentacao,
)
from services.formatacao import formatar_moeda, formatar_percentual
from services.juros import TAXA_DIARIA, calcular_juros

st.set_page_config(
    page_title="Gestor Comercial",
    layout="wide",
    menu_items={"Get help": None, "Report a bug": None, "About": "Gestor Comercial"},
)

st.markdown(
    """
    <style>
    .block-container { padding-top: 2rem; max-width: 1100px; }
    h1 { font-weight: 600; letter-spacing: -0.5px; }
    [data-testid="stAppDeployButton"], .stDeployButton, [data-testid="stDeployButton"] { display: none; }
    </style>
    """,
    unsafe_allow_html=True,
)


def mostrar_tabela(linhas: list[dict]) -> None:
    st.dataframe(pd.DataFrame(linhas), hide_index=True, width="stretch")


def aba_comissoes() -> None:
    titulo, ajuda = st.columns([0.92, 0.08], vertical_alignment="center")
    titulo.subheader("Cálculo de comissões")
    with ajuda.popover("?", help="Como a comissão é calculada"):
        st.markdown(
            """
**Como a comissão é calculada**

A faixa é definida pelo valor de cada venda, individualmente:

| Valor da venda | Comissão |
|---|---|
| Abaixo de R$ 100,00 | 0% |
| De R$ 100,00 até abaixo de R$ 500,00 | 1% |
| A partir de R$ 500,00 | 5% |

1. Cada venda recebe o percentual da sua faixa.
2. A comissão da venda é o valor multiplicado pelo percentual, arredondada para 2 casas (0,005 ou mais sobe para o centavo seguinte).
3. A comissão total do vendedor é a soma das comissões já arredondadas.
4. A comissão geral é a soma das comissões de todos os vendedores.

A faixa nunca é aplicada sobre o total do vendedor.

Exemplo: uma venda de R$ 1.200,50 gera 5% = R$ 60,025, arredondado para R$ 60,03.
"""
        )

    arquivo = st.file_uploader("Carregar arquivo JSON de vendas", type=["json"], key="arquivo_vendas")
    if arquivo is None:
        st.info("Selecione um arquivo JSON para calcular as comissões.")
        return

    try:
        resultado = processar_texto_json(arquivo.getvalue())
    except ErroValidacaoComissoes as erro:
        st.error("O arquivo contém problemas e não foi processado:")
        for mensagem in erro.erros:
            st.text(f"- {mensagem}")
        return

    st.success(f"Arquivo processado: {len(resultado.vendas)} vendas de {len(resultado.resumo_por_vendedor)} vendedores.")

    coluna_total, coluna_vendas = st.columns(2)
    coluna_total.metric("Comissão geral", formatar_moeda(resultado.comissao_geral))
    coluna_vendas.metric("Vendas processadas", len(resultado.vendas))

    st.markdown("#### Resumo por vendedor")
    mostrar_tabela(
        [
            {
                "Vendedor": r.vendedor,
                "Vendas": r.quantidade_vendas,
                "Total vendido": formatar_moeda(r.total_vendido),
                "Comissão total": formatar_moeda(r.total_comissao),
            }
            for r in resultado.resumo_por_vendedor
        ]
    )

    st.markdown("#### Vendas processadas")
    mostrar_tabela(
        [
            {
                "Vendedor": v.vendedor,
                "Valor da venda": formatar_moeda(v.valor),
                "Percentual": formatar_percentual(v.taxa),
                "Comissão": formatar_moeda(v.comissao),
            }
            for v in resultado.vendas
        ]
    )


def aba_estoque(conexao) -> None:
    st.subheader("Controle de estoque")

    aviso = st.session_state.pop("aviso_estoque", None)
    if aviso:
        tipo_aviso, texto = aviso
        (st.success if tipo_aviso == "sucesso" else st.error)(texto)

    produtos = listar_produtos(conexao)

    st.markdown("#### Estoque atual")
    mostrar_tabela(
        [{"Código": p["codigo"], "Descrição": p["descricao"], "Quantidade": p["estoque"]} for p in produtos]
    )

    st.markdown("#### Registrar movimentação")
    rotulos = {p["codigo"]: f"{p['codigo']} - {p['descricao']} (estoque: {p['estoque']})" for p in produtos}
    with st.form("form_movimentacao", clear_on_submit=True):
        codigo = st.selectbox("Produto", list(rotulos), format_func=rotulos.get)
        tipo = st.radio("Tipo", TIPOS_MOVIMENTACAO, horizontal=True)
        quantidade = st.number_input("Quantidade", min_value=0, step=1, value=0)
        descricao = st.text_input("Descrição / motivo")
        enviado = st.form_submit_button("Registrar movimentação", type="primary")

    if enviado:
        try:
            r = registrar_movimentacao(conexao, codigo, tipo, int(quantidade), descricao)
            st.session_state["aviso_estoque"] = (
                "sucesso",
                f"Movimentação realizada. Produto: {r.descricao_produto}. "
                f"Estoque anterior: {r.saldo_anterior}. Estoque atual: {r.saldo_posterior}.",
            )
        except ErroEstoque as erro:
            st.session_state["aviso_estoque"] = ("erro", f"Movimentação rejeitada. {erro}")
        st.rerun()

    st.markdown("#### Histórico de movimentações")
    historico = listar_movimentacoes(conexao)
    if not historico:
        st.info("Nenhuma movimentação registrada.")
        return
    mostrar_tabela(
        [
            {
                "ID": m["id"],
                "Data e hora": datetime.fromisoformat(m["data_hora"]).strftime("%d/%m/%Y %H:%M:%S"),
                "Produto": f"{m['codigo_produto']} - {m['produto']}",
                "Tipo": m["tipo"],
                "Quantidade": m["quantidade"],
                "Descrição": m["descricao"],
                "Saldo anterior": m["saldo_anterior"],
                "Saldo posterior": m["saldo_posterior"],
            }
            for m in historico
        ]
    )


def aba_juros() -> None:
    st.subheader("Calculadora de juros")
    st.info(
        "Cálculo de juros simples de 2,5% ao dia sobre o valor original, "
        "contando dias corridos completos de atraso. Não há multa nem juros mensais."
    )

    with st.form("form_juros"):
        valor = st.number_input("Valor original (R$)", min_value=0.0, step=0.01, format="%.2f")
        vencimento = st.date_input("Data de vencimento", value=date.today(), format="DD/MM/YYYY")
        calcular = st.form_submit_button("Calcular juros", type="primary")

    if not calcular:
        return

    try:
        r = calcular_juros(Decimal(str(valor)), vencimento)
    except ValueError as erro:
        st.error(str(erro))
        return

    if r.dias_atraso == 0:
        st.success("Pagamento em dia: não há juros a cobrar.")
    else:
        st.warning(f"Pagamento em atraso há {r.dias_atraso} dia(s).")

    mostrar_tabela(
        [
            {"Item": "Valor original", "Valor": formatar_moeda(r.valor_original)},
            {"Item": "Data de vencimento", "Valor": r.data_vencimento.strftime("%d/%m/%Y")},
            {"Item": "Data de cálculo", "Valor": r.data_calculo.strftime("%d/%m/%Y")},
            {"Item": "Dias em atraso", "Valor": str(r.dias_atraso)},
            {"Item": "Taxa diária", "Valor": formatar_percentual(TAXA_DIARIA)},
            {"Item": "Valor dos juros", "Valor": formatar_moeda(r.juros)},
            {"Item": "Valor final atualizado", "Valor": formatar_moeda(r.total)},
        ]
    )


st.title("Gestor Comercial")

conexao = conectar()
try:
    tab_comissoes, tab_estoque, tab_juros = st.tabs(["Comissões", "Estoque", "Calculadora de Juros"])
    with tab_comissoes:
        aba_comissoes()
    with tab_estoque:
        aba_estoque(conexao)
    with tab_juros:
        aba_juros()
finally:
    conexao.close()
