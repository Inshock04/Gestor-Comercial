from dataclasses import dataclass
from datetime import date
from decimal import ROUND_HALF_UP, Decimal

TAXA_DIARIA = Decimal("0.025")
CENTAVOS = Decimal("0.01")
VALOR_MAXIMO = Decimal("1000000000000")


@dataclass(frozen=True)
class ResultadoJuros:
    valor_original: Decimal
    data_vencimento: date
    data_calculo: date
    dias_atraso: int
    taxa_diaria: Decimal
    juros: Decimal
    total: Decimal


def calcular_dias_atraso(vencimento: date, data_calculo: date) -> int:
    """Dias corridos completos de atraso; zero se ainda nao venceu."""
    return max((data_calculo - vencimento).days, 0)


def calcular_juros(
    valor_original: Decimal,
    vencimento: date,
    data_calculo: date | None = None,
) -> ResultadoJuros:
    """Juros simples de 2,5% ao dia sobre o valor original."""
    if not isinstance(valor_original, Decimal) or not valor_original.is_finite():
        raise ValueError("Informe um valor monetario valido.")
    if valor_original < 0:
        raise ValueError("O valor original nao pode ser negativo.")
    if valor_original > VALOR_MAXIMO:
        raise ValueError("O valor original excede o limite permitido.")
    if not isinstance(vencimento, date):
        raise ValueError("Informe uma data de vencimento valida.")

    data_calculo = data_calculo or date.today()
    valor = valor_original.quantize(CENTAVOS, rounding=ROUND_HALF_UP)
    dias = calcular_dias_atraso(vencimento, data_calculo)
    juros = (valor * TAXA_DIARIA * dias).quantize(CENTAVOS, rounding=ROUND_HALF_UP)

    return ResultadoJuros(valor, vencimento, data_calculo, dias, TAXA_DIARIA, juros, valor + juros)
