import sqlite3

import pytest

from database.conexao import conectar
from services.estoque import (
    ErroEstoque,
    listar_movimentacoes,
    listar_produtos,
    registrar_movimentacao,
)


@pytest.fixture
def banco(tmp_path):
    conexao = conectar(tmp_path / "teste.db")
    yield conexao
    conexao.close()


def saldo(conexao, codigo):
    return conexao.execute("SELECT estoque FROM produtos WHERE codigo = ?", (codigo,)).fetchone()[0]


def test_estoque_inicial_carregado_do_json(banco):
    produtos = {p["codigo"]: p["estoque"] for p in listar_produtos(banco)}
    assert produtos == {101: 150, 102: 75, 103: 200, 104: 320, 105: 90}


def test_entrada_aumenta_saldo(banco):
    resultado = registrar_movimentacao(banco, 101, "Entrada", 30, "Compra")
    assert (resultado.saldo_anterior, resultado.saldo_posterior) == (150, 180)
    assert saldo(banco, 101) == 180


def test_saida_reduz_saldo(banco):
    resultado = registrar_movimentacao(banco, 101, "Saída", 20, "Venda")
    assert (resultado.saldo_anterior, resultado.saldo_posterior) == (150, 130)
    assert saldo(banco, 101) == 130


def test_saida_de_todo_o_estoque_e_permitida(banco):
    registrar_movimentacao(banco, 105, "Saída", 90, "Baixa total")
    assert saldo(banco, 105) == 0


def test_saida_maior_que_estoque_e_rejeitada_sem_alterar_nada(banco):
    with pytest.raises(ErroEstoque):
        registrar_movimentacao(banco, 101, "Saída", 151, "Venda")
    assert saldo(banco, 101) == 150
    assert listar_movimentacoes(banco) == []


@pytest.mark.parametrize("quantidade", [0, -1, -50, 1.5, "10", None, True])
def test_quantidade_invalida(banco, quantidade):
    with pytest.raises(ErroEstoque):
        registrar_movimentacao(banco, 101, "Entrada", quantidade, "Teste")
    assert saldo(banco, 101) == 150


@pytest.mark.parametrize("descricao", ["", "   ", None])
def test_descricao_obrigatoria(banco, descricao):
    with pytest.raises(ErroEstoque):
        registrar_movimentacao(banco, 101, "Entrada", 1, descricao)
    assert listar_movimentacoes(banco) == []


def test_produto_inexistente(banco):
    with pytest.raises(ErroEstoque):
        registrar_movimentacao(banco, 999, "Entrada", 1, "Teste")
    assert listar_movimentacoes(banco) == []


def test_tipo_invalido(banco):
    with pytest.raises(ErroEstoque):
        registrar_movimentacao(banco, 101, "Transferencia", 1, "Teste")


def test_identificadores_unicos_e_crescentes(banco):
    ids = [registrar_movimentacao(banco, 101, "Entrada", 1, f"Mov {i}").id for i in range(5)]
    assert len(set(ids)) == 5
    assert ids == sorted(ids)


def test_historico_guarda_todos_os_campos(banco):
    registrar_movimentacao(banco, 102, "Saída", 5, "Venda balcao")
    historico = listar_movimentacoes(banco)
    assert len(historico) == 1
    mov = historico[0]
    assert mov["codigo_produto"] == 102
    assert mov["produto"] == "Caderno Universitário"
    assert mov["tipo"] == "Saída"
    assert mov["quantidade"] == 5
    assert mov["descricao"] == "Venda balcao"
    assert (mov["saldo_anterior"], mov["saldo_posterior"]) == (75, 70)
    assert mov["data_hora"]


def test_persistencia_apos_reabrir_o_banco(tmp_path):
    caminho = tmp_path / "persistente.db"
    primeira = conectar(caminho)
    registrar_movimentacao(primeira, 101, "Saída", 20, "Venda")
    primeira.close()

    segunda = conectar(caminho)
    assert saldo(segunda, 101) == 130
    assert len(listar_movimentacoes(segunda)) == 1
    segunda.close()


def test_estoque_inicial_nao_e_recarregado(tmp_path):
    caminho = tmp_path / "unico.db"
    conectar(caminho).close()
    conexao = conectar(caminho)
    registrar_movimentacao(conexao, 103, "Entrada", 10, "Compra")
    conexao.close()

    conexao = conectar(caminho)
    assert saldo(conexao, 103) == 210
    conexao.close()


def test_falha_no_historico_desfaz_a_atualizacao_do_saldo(banco):
    banco.execute(
        "CREATE TRIGGER falha_historico BEFORE INSERT ON movimentacoes "
        "BEGIN SELECT RAISE(ABORT, 'falha simulada'); END"
    )
    with pytest.raises(sqlite3.DatabaseError):
        registrar_movimentacao(banco, 101, "Saída", 20, "Venda")
    assert saldo(banco, 101) == 150
    assert listar_movimentacoes(banco) == []
    assert not banco.in_transaction



def test_quantidade_acima_do_limite_do_banco_e_rejeitada(banco):
    with pytest.raises(ErroEstoque):
        registrar_movimentacao(banco, 101, "Entrada", 2**63, "Teste")
    assert saldo(banco, 101) == 150


def test_entrada_que_estoura_o_saldo_maximo_e_rejeitada(banco):
    with pytest.raises(ErroEstoque):
        registrar_movimentacao(banco, 101, "Entrada", 2**63 - 1, "Teste")
    assert saldo(banco, 101) == 150
    assert listar_movimentacoes(banco) == []
    assert not banco.in_transaction


def test_codigo_de_produto_malicioso_nao_executa_sql(banco):
    with pytest.raises(ErroEstoque):
        registrar_movimentacao(banco, "101; DROP TABLE produtos", "Entrada", 1, "Teste")
    assert len(listar_produtos(banco)) == 5
