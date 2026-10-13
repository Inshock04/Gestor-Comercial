from decimal import ROUND_HALF_UP, Decimal

CENTAVOS = Decimal("0.01")


def formatar_moeda(valor: Decimal) -> str:
    """Formata um Decimal como moeda brasileira, por exemplo R$ 1.234,56."""
    valor = valor.quantize(CENTAVOS, rounding=ROUND_HALF_UP)
    texto = f"{valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    return f"R$ {texto}"


def formatar_percentual(taxa: Decimal) -> str:
    """Formata uma taxa decimal (0.05) como percentual (5%)."""
    percentual = (taxa * 100).normalize()
    return f"{percentual:f}".replace(".", ",") + "%"
