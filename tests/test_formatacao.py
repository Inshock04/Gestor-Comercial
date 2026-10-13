from decimal import Decimal

import pytest

from services.formatacao import formatar_moeda, formatar_percentual


@pytest.mark.parametrize(
    "valor, esperado",
    [
        ("0", "R$ 0,00"),
        ("1746.02", "R$ 1.746,02"),
        ("1234567.8", "R$ 1.234.567,80"),
        ("0.125", "R$ 0,13"),
        ("2.675", "R$ 2,68"),
    ],
)
def test_formatar_moeda(valor, esperado):
    assert formatar_moeda(Decimal(valor)) == esperado


@pytest.mark.parametrize(
    "taxa, esperado",
    [("0", "0%"), ("0.01", "1%"), ("0.05", "5%"), ("0.025", "2,5%")],
)
def test_formatar_percentual(taxa, esperado):
    assert formatar_percentual(Decimal(taxa)) == esperado
