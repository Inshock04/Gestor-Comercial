from datetime import date
from decimal import Decimal

import pytest

from services.juros import TAXA_DIARIA, calcular_juros

HOJE = date(2025, 6, 20)


def test_vencimento_hoje_sem_juros():
    r = calcular_juros(Decimal("1000.00"), HOJE, HOJE)
    assert r.dias_atraso == 0
    assert r.juros == Decimal("0.00")
    assert r.total == Decimal("1000.00")


def test_vencimento_futuro_sem_juros():
    r = calcular_juros(Decimal("1000.00"), date(2025, 7, 1), HOJE)
    assert r.dias_atraso == 0
    assert r.juros == Decimal("0.00")


def test_atraso_de_um_dia():
    r = calcular_juros(Decimal("1000.00"), date(2025, 6, 19), HOJE)
    assert r.dias_atraso == 1
    assert r.juros == Decimal("25.00")
    assert r.total == Decimal("1025.00")


def test_atraso_de_dez_dias():
    r = calcular_juros(Decimal("1000.00"), date(2025, 6, 10), HOJE)
    assert r.dias_atraso == 10
    assert r.juros == Decimal("250.00")
    assert r.total == Decimal("1250.00")


def test_taxa_diaria_e_dois_virgula_cinco_por_cento():
    assert TAXA_DIARIA == Decimal("0.025")
    assert calcular_juros(Decimal("100"), date(2025, 6, 19), HOJE).taxa_diaria == Decimal("0.025")


def test_juros_simples_nao_compostos():
    r = calcular_juros(Decimal("200.00"), date(2025, 5, 21), HOJE)
    assert r.dias_atraso == 30
    assert r.juros == Decimal("150.00")


def test_arredondamento_para_duas_casas():
    r = calcular_juros(Decimal("10.01"), date(2025, 6, 19), HOJE)
    assert r.juros == Decimal("0.25")
    assert r.total == Decimal("10.26")


def test_data_atual_padrao_e_a_do_sistema():
    r = calcular_juros(Decimal("100.00"), date.today())
    assert r.data_calculo == date.today()
    assert r.dias_atraso == 0


def test_valor_negativo_e_rejeitado():
    with pytest.raises(ValueError):
        calcular_juros(Decimal("-1"), HOJE, HOJE)


@pytest.mark.parametrize("valor", [1000, "100", None, Decimal("NaN")])
def test_valor_invalido(valor):
    with pytest.raises(ValueError):
        calcular_juros(valor, HOJE, HOJE)


def test_data_invalida():
    with pytest.raises(ValueError):
        calcular_juros(Decimal("100"), "2025-06-10", HOJE)


@pytest.mark.parametrize("valor", [Decimal("1e30"), Decimal("1e999999")])
def test_valor_acima_do_limite_e_rejeitado(valor):
    with pytest.raises(ValueError):
        calcular_juros(valor, HOJE, HOJE)
