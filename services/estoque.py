import sqlite3
from dataclasses import dataclass
from datetime import datetime

TIPOS_MOVIMENTACAO = ("Entrada", "Saída")
LIMITE_INTEIRO = 2**63 - 1


class ErroEstoque(Exception):
    """Movimentacao rejeitada por violar uma regra de negocio."""


@dataclass(frozen=True)
class ResultadoMovimentacao:
    id: int
    codigo_produto: int
    descricao_produto: str
    tipo: str
    quantidade: int
    saldo_anterior: int
    saldo_posterior: int


def listar_produtos(conexao: sqlite3.Connection) -> list[sqlite3.Row]:
    return conexao.execute(
        "SELECT codigo, descricao, estoque FROM produtos ORDER BY codigo"
    ).fetchall()


def listar_movimentacoes(conexao: sqlite3.Connection) -> list[sqlite3.Row]:
    return conexao.execute(
        """
        SELECT m.id, m.data_hora, m.codigo_produto, p.descricao AS produto, m.tipo,
               m.quantidade, m.descricao, m.saldo_anterior, m.saldo_posterior
        FROM movimentacoes m
        JOIN produtos p ON p.codigo = m.codigo_produto
        ORDER BY m.id DESC
        """
    ).fetchall()


def _validar_entrada(tipo: str, quantidade: int, descricao: str) -> str:
    if tipo not in TIPOS_MOVIMENTACAO:
        raise ErroEstoque("Tipo de movimentacao invalido. Use Entrada ou Saída.")
    if isinstance(quantidade, bool) or not isinstance(quantidade, int) or quantidade <= 0:
        raise ErroEstoque("A quantidade deve ser um numero inteiro maior que zero.")
    if quantidade > LIMITE_INTEIRO:
        raise ErroEstoque("Quantidade acima do limite permitido.")
    descricao = (descricao or "").strip()
    if not descricao:
        raise ErroEstoque("Informe a descricao ou o motivo da movimentacao.")
    return descricao


def registrar_movimentacao(
    conexao: sqlite3.Connection,
    codigo_produto: int,
    tipo: str,
    quantidade: int,
    descricao: str,
) -> ResultadoMovimentacao:
    """Atualiza o estoque e grava o historico na mesma transacao."""
    descricao = _validar_entrada(tipo, quantidade, descricao)

    conexao.execute("BEGIN IMMEDIATE")
    try:
        produto = conexao.execute(
            "SELECT descricao, estoque FROM produtos WHERE codigo = ?", (codigo_produto,)
        ).fetchone()
        if produto is None:
            raise ErroEstoque("Produto inexistente.")

        saldo_anterior = produto["estoque"]
        if tipo == "Saída" and quantidade > saldo_anterior:
            raise ErroEstoque(
                f"Saida rejeitada: estoque disponivel de {saldo_anterior}, "
                f"quantidade solicitada de {quantidade}."
            )
        saldo_posterior = saldo_anterior + quantidade if tipo == "Entrada" else saldo_anterior - quantidade
        if saldo_posterior > LIMITE_INTEIRO:
            raise ErroEstoque("Entrada rejeitada: o saldo ultrapassaria o limite permitido.")

        conexao.execute(
            "UPDATE produtos SET estoque = ? WHERE codigo = ?", (saldo_posterior, codigo_produto)
        )
        cursor = conexao.execute(
            """
            INSERT INTO movimentacoes
                (data_hora, codigo_produto, tipo, quantidade, descricao, saldo_anterior, saldo_posterior)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                datetime.now().isoformat(timespec="seconds"),
                codigo_produto,
                tipo,
                quantidade,
                descricao,
                saldo_anterior,
                saldo_posterior,
            ),
        )
        conexao.execute("COMMIT")
    except Exception:
        conexao.execute("ROLLBACK")
        raise

    return ResultadoMovimentacao(
        cursor.lastrowid, codigo_produto, produto["descricao"], tipo, quantidade,
        saldo_anterior, saldo_posterior,
    )
