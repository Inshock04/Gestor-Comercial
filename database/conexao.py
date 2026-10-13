import json
import sqlite3
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
CAMINHO_BANCO = RAIZ / "data" / "gestor.db"
CAMINHO_ESTOQUE_INICIAL = RAIZ / "data" / "estoque.json"

ESQUEMA = """
CREATE TABLE IF NOT EXISTS produtos (
    codigo INTEGER PRIMARY KEY,
    descricao TEXT NOT NULL,
    estoque INTEGER NOT NULL CHECK (estoque >= 0)
);

CREATE TABLE IF NOT EXISTS movimentacoes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    data_hora TEXT NOT NULL,
    codigo_produto INTEGER NOT NULL REFERENCES produtos (codigo),
    tipo TEXT NOT NULL CHECK (tipo IN ('Entrada', 'Saída')),
    quantidade INTEGER NOT NULL CHECK (quantidade > 0),
    descricao TEXT NOT NULL,
    saldo_anterior INTEGER NOT NULL,
    saldo_posterior INTEGER NOT NULL
);
"""


def conectar(caminho: Path | str = CAMINHO_BANCO) -> sqlite3.Connection:
    """Abre a conexao, cria as tabelas e carrega o estoque inicial se o banco for novo.

    A conexao usa controle manual de transacoes (isolation_level=None).
    """
    Path(caminho).parent.mkdir(parents=True, exist_ok=True)
    conexao = sqlite3.connect(caminho, isolation_level=None)
    conexao.row_factory = sqlite3.Row
    conexao.execute("PRAGMA foreign_keys = ON")
    conexao.executescript(ESQUEMA)
    _carregar_estoque_inicial(conexao)
    return conexao


def _carregar_estoque_inicial(conexao: sqlite3.Connection, caminho: Path = CAMINHO_ESTOQUE_INICIAL) -> None:
    """Insere os produtos do JSON somente quando a tabela de produtos esta vazia."""
    if conexao.execute("SELECT COUNT(*) FROM produtos").fetchone()[0] > 0:
        return
    with open(caminho, encoding="utf-8") as arquivo:
        itens = json.load(arquivo)["estoque"]
    conexao.execute("BEGIN")
    try:
        conexao.executemany(
            "INSERT INTO produtos (codigo, descricao, estoque) VALUES (?, ?, ?)",
            [(i["codigoProduto"], i["descricaoProduto"], i["estoque"]) for i in itens],
        )
        conexao.execute("COMMIT")
    except Exception:
        conexao.execute("ROLLBACK")
        raise
