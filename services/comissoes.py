import json
from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation
from typing import Any

CENTAVOS = Decimal("0.01")
LIMITE_FAIXA_1 = Decimal("100.00")
LIMITE_FAIXA_2 = Decimal("500.00")
TAXA_FAIXA_0 = Decimal("0")
TAXA_FAIXA_1 = Decimal("0.01")
TAXA_FAIXA_2 = Decimal("0.05")
VALOR_MAXIMO = Decimal("1000000000000")


class ErroValidacaoComissoes(Exception):
    """Erro de estrutura ou de conteudo no JSON de vendas."""

    def __init__(self, erros: list[str]):
        self.erros = erros
        super().__init__("; ".join(erros))


@dataclass(frozen=True)
class VendaProcessada:
    vendedor: str
    valor: Decimal
    taxa: Decimal
    comissao: Decimal


@dataclass(frozen=True)
class ResumoVendedor:
    vendedor: str
    quantidade_vendas: int
    total_vendido: Decimal
    total_comissao: Decimal


@dataclass(frozen=True)
class ResultadoComissoes:
    vendas: list[VendaProcessada]
    resumo_por_vendedor: list[ResumoVendedor]
    comissao_geral: Decimal


def obter_taxa_comissao(valor: Decimal) -> Decimal:
    """Retorna a taxa de comissao de uma venda individual."""
    if valor < LIMITE_FAIXA_1:
        return TAXA_FAIXA_0
    if valor < LIMITE_FAIXA_2:
        return TAXA_FAIXA_1
    return TAXA_FAIXA_2


def calcular_comissao(valor: Decimal) -> Decimal:
    """Comissao de uma venda, arredondada para centavos com ROUND_HALF_UP."""
    return (valor * obter_taxa_comissao(valor)).quantize(CENTAVOS, rounding=ROUND_HALF_UP)


def _converter_valor(bruto: Any) -> Decimal | None:
    if isinstance(bruto, bool) or not isinstance(bruto, (int, float, str)):
        return None
    texto = str(bruto).strip()
    if "_" in texto:
        return None
    try:
        valor = Decimal(texto)
    except InvalidOperation:
        return None
    return valor if valor.is_finite() else None


def validar_vendas(dados: Any) -> list[tuple[str, Decimal]]:
    """Valida a estrutura do JSON e devolve pares (vendedor, valor).

    Todos os problemas encontrados sao reunidos em um unico erro.
    """
    if not isinstance(dados, dict) or "vendas" not in dados:
        raise ErroValidacaoComissoes(['O arquivo deve conter um objeto com a chave "vendas".'])
    if not isinstance(dados["vendas"], list):
        raise ErroValidacaoComissoes(['A chave "vendas" deve ser uma lista.'])
    if not dados["vendas"]:
        raise ErroValidacaoComissoes(['A lista "vendas" esta vazia.'])

    erros: list[str] = []
    vendas: list[tuple[str, Decimal]] = []

    for posicao, registro in enumerate(dados["vendas"], start=1):
        rotulo = f"Registro {posicao}"
        if not isinstance(registro, dict):
            erros.append(f"{rotulo}: deve ser um objeto com vendedor e valor.")
            continue

        vendedor = registro.get("vendedor")
        if not isinstance(vendedor, str) or not vendedor.strip():
            erros.append(f"{rotulo}: vendedor ausente ou vazio.")
            continue

        if "valor" not in registro:
            erros.append(f"{rotulo} ({vendedor.strip()}): campo valor ausente.")
            continue

        valor = _converter_valor(registro["valor"])
        if valor is None:
            erros.append(f"{rotulo} ({vendedor.strip()}): valor invalido ({registro['valor']!r}).")
        elif valor < 0:
            erros.append(f"{rotulo} ({vendedor.strip()}): valor negativo ({registro['valor']}).")
        elif valor > VALOR_MAXIMO:
            erros.append(f"{rotulo} ({vendedor.strip()}): valor acima do limite permitido (R$ 1.000.000.000.000,00).")
        else:
            vendas.append((vendedor.strip(), valor))

    if erros:
        raise ErroValidacaoComissoes(erros)
    return vendas


def processar_vendas(dados: Any) -> ResultadoComissoes:
    """Calcula a comissao de cada venda e agrupa os resultados por vendedor."""
    vendas = [
        VendaProcessada(vendedor, valor, obter_taxa_comissao(valor), calcular_comissao(valor))
        for vendedor, valor in validar_vendas(dados)
    ]

    acumulado: dict[str, list[Decimal | int]] = {}
    for venda in vendas:
        item = acumulado.setdefault(venda.vendedor, [0, Decimal("0"), Decimal("0")])
        item[0] += 1
        item[1] += venda.valor
        item[2] += venda.comissao

    resumo = [
        ResumoVendedor(nome, qtd, total, comissao)
        for nome, (qtd, total, comissao) in acumulado.items()
    ]
    comissao_geral = sum((r.total_comissao for r in resumo), Decimal("0"))
    return ResultadoComissoes(vendas, resumo, comissao_geral)


def processar_texto_json(texto: str | bytes) -> ResultadoComissoes:
    """Le o conteudo bruto de um arquivo JSON e processa as vendas."""
    try:
        dados = json.loads(texto)
    except (json.JSONDecodeError, UnicodeDecodeError, RecursionError) as erro:
        raise ErroValidacaoComissoes([f"O arquivo nao e um JSON valido: {erro}"]) from erro
    return processar_vendas(dados)
