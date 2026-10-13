import json
from decimal import Decimal
from pathlib import Path

import pytest

from services.comissoes import (
    ErroValidacaoComissoes,
    calcular_comissao,
    obter_taxa_comissao,
    processar_texto_json,
    processar_vendas,
)

ARQUIVO_VENDAS = Path(__file__).resolve().parent.parent / "data" / "vendas.json"


@pytest.mark.parametrize(
    "valor, taxa, comissao",
    [
        ("99.99", "0", "0.00"),
        ("100.00", "0.01", "1.00"),
        ("499.99", "0.01", "5.00"),
        ("500.00", "0.05", "25.00"),
    ],
)
def test_faixas_de_comissao(valor, taxa, comissao):
    assert obter_taxa_comissao(Decimal(valor)) == Decimal(taxa)
    assert calcular_comissao(Decimal(valor)) == Decimal(comissao)


def test_arredondamento_half_up():
    assert calcular_comissao(Decimal("1200.50")) == Decimal("60.03")
    assert calcular_comissao(Decimal("1400.30")) == Decimal("70.02")


def test_regra_aplicada_por_venda_e_nao_pelo_total():
    dados = {"vendas": [{"vendedor": "A", "valor": 400}, {"vendedor": "A", "valor": 400}]}
    resultado = processar_vendas(dados)
    assert resultado.resumo_por_vendedor[0].total_comissao == Decimal("8.00")


def test_agrupamento_por_vendedor():
    dados = {
        "vendas": [
            {"vendedor": "A", "valor": 1000},
            {"vendedor": "B", "valor": 100},
            {"vendedor": "A", "valor": 100},
        ]
    }
    resultado = processar_vendas(dados)
    resumo = {r.vendedor: r for r in resultado.resumo_por_vendedor}
    assert resumo["A"].quantidade_vendas == 2
    assert resumo["A"].total_vendido == Decimal("1100")
    assert resumo["A"].total_comissao == Decimal("51.00")
    assert resumo["B"].total_comissao == Decimal("1.00")
    assert resultado.comissao_geral == Decimal("52.00")


def test_vendas_iguais_nao_sao_descartadas():
    dados = {"vendas": [{"vendedor": "A", "valor": 500}] * 2}
    resultado = processar_vendas(dados)
    assert len(resultado.vendas) == 2
    assert resultado.comissao_geral == Decimal("50.00")


def test_json_do_desafio_gera_resultados_esperados():
    resultado = processar_texto_json(ARQUIVO_VENDAS.read_bytes())
    por_vendedor = {r.vendedor: r.total_comissao for r in resultado.resumo_por_vendedor}
    assert por_vendedor == {
        "João Silva": Decimal("495.69"),
        "Maria Souza": Decimal("465.96"),
        "Carlos Oliveira": Decimal("379.38"),
        "Ana Lima": Decimal("404.99"),
    }
    assert resultado.comissao_geral == Decimal("1746.02")


def test_json_malformado():
    with pytest.raises(ErroValidacaoComissoes):
        processar_texto_json("{ isto nao e json")


@pytest.mark.parametrize(
    "dados",
    [[], {}, {"vendas": "texto"}, {"vendas": []}],
)
def test_estrutura_invalida(dados):
    with pytest.raises(ErroValidacaoComissoes):
        processar_vendas(dados)


@pytest.mark.parametrize(
    "registro, trecho",
    [
        ({"vendedor": "", "valor": 10}, "vendedor ausente ou vazio"),
        ({"vendedor": "   ", "valor": 10}, "vendedor ausente ou vazio"),
        ({"valor": 10}, "vendedor ausente ou vazio"),
        ({"vendedor": "A", "valor": -5}, "valor negativo"),
        ({"vendedor": "A", "valor": "abc"}, "valor invalido"),
        ({"vendedor": "A", "valor": None}, "valor invalido"),
        ({"vendedor": "A", "valor": True}, "valor invalido"),
        ({"vendedor": "A", "valor": "NaN"}, "valor invalido"),
        ({"vendedor": "A"}, "campo valor ausente"),
        ("texto", "deve ser um objeto"),
    ],
)
def test_registros_invalidos_indicam_o_registro(registro, trecho):
    dados = {"vendas": [{"vendedor": "Ok", "valor": 10}, registro]}
    with pytest.raises(ErroValidacaoComissoes) as erro:
        processar_vendas(dados)
    assert len(erro.value.erros) == 1
    assert erro.value.erros[0].startswith("Registro 2")
    assert trecho in erro.value.erros[0]


def test_todos_os_erros_sao_reportados():
    dados = {"vendas": [{"vendedor": "", "valor": 1}, {"vendedor": "A", "valor": -1}]}
    with pytest.raises(ErroValidacaoComissoes) as erro:
        processar_vendas(dados)
    assert len(erro.value.erros) == 2


def test_valor_decimal_sem_erro_de_ponto_flutuante():
    texto = json.dumps({"vendas": [{"vendedor": "A", "valor": 0.1}] * 3 + [{"vendedor": "A", "valor": 500.10}]})
    resultado = processar_texto_json(texto)
    assert resultado.resumo_por_vendedor[0].total_vendido == Decimal("500.40")
    assert resultado.comissao_geral == Decimal("25.01")


def test_venda_de_valor_zero_e_aceita_sem_comissao():
    resultado = processar_vendas({"vendas": [{"vendedor": "A", "valor": 0}]})
    assert resultado.comissao_geral == Decimal("0.00")
    assert resultado.vendas[0].taxa == Decimal("0")


def test_espacos_no_nome_do_vendedor_sao_ignorados_no_agrupamento():
    dados = {"vendas": [{"vendedor": " A ", "valor": 500}, {"vendedor": "A", "valor": 500}]}
    resultado = processar_vendas(dados)
    assert len(resultado.resumo_por_vendedor) == 1
    assert resultado.resumo_por_vendedor[0].quantidade_vendas == 2


def test_json_muito_aninhado_nao_derruba_o_sistema():
    with pytest.raises(ErroValidacaoComissoes):
        processar_texto_json("[" * 200000)


@pytest.mark.parametrize("valor", [1e30, "1e999999999", 10**13, "1_000"])
def test_valores_absurdos_ou_formato_estranho_sao_rejeitados(valor):
    with pytest.raises(ErroValidacaoComissoes):
        processar_vendas({"vendas": [{"vendedor": "A", "valor": valor}]})
