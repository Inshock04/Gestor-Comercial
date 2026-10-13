# Gestor Comercial

Sistema com três módulos: cálculo de comissões a partir de JSON, controle de estoque com SQLite e calculadora de juros por atraso.

Tecnologias: Python, Streamlit, SQLite e Pytest.

## Escolha da tecnologia: Streamlit

Para o desenvolvimento deste projeto, optamos pelo **Streamlit**, uma biblioteca Python que permite criar interfaces web de maneira simples e rápida.

A escolha foi feita considerando o objetivo do desafio: desenvolver um sistema funcional para calcular comissões, controlar movimentações de estoque e calcular juros por atraso.

### Por que Streamlit e não FastAPI?

O **FastAPI** é uma excelente ferramenta para desenvolver APIs REST e integrar diferentes sistemas. Entretanto, nosso projeto não exige uma API para comunicação com serviços externos ou um frontend separado.

O Streamlit permite trabalhar diretamente com Python, oferecendo recursos prontos para formulários, tabelas, upload de arquivos JSON e apresentação dos resultados.

### Vantagens para o projeto

- **Simplicidade:** menos código e menor complexidade.
- **Agilidade:** desenvolvimento rápido das três funcionalidades.
- **Interface intuitiva:** fácil utilização, sem conhecimentos técnicos.
- **Manutenção:** estrutura simples e regras de negócio organizadas.
- **Menos dependências:** não exige um frontend separado nem uma API REST.

### Conclusão

A escolha do Streamlit foi uma decisão técnica baseada nas necessidades do projeto, priorizando simplicidade, funcionalidade e facilidade de manutenção.

O FastAPI seria mais adequado caso o sistema precisasse futuramente fornecer serviços para outras aplicações, integrar diferentes clientes ou disponibilizar endpoints REST.

**Nosso objetivo não foi utilizar a tecnologia mais complexa, mas escolher a ferramenta mais adequada para resolver o problema proposto.**

## Instalação e execução (Windows)

Requer Python 3.10 ou superior.

```powershell
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
streamlit run app.py
```

Testes:

```powershell
python -m pytest
```

## Estrutura

```
app.py                  interface Streamlit
services/comissoes.py   regras e validação de comissões
services/estoque.py     movimentações de estoque
services/juros.py       cálculo de juros
services/formatacao.py  formatação de R$ e percentuais
database/conexao.py     conexão SQLite, criação das tabelas e carga inicial
data/vendas.json        vendas de exemplo
data/estoque.json       estoque inicial
data/gestor.db          banco criado na primeira execução
tests/                  testes automatizados
```

As regras de negócio não dependem do Streamlit.

## Regras e hipóteses adotadas

**Comissões**
- Abaixo de R$ 100,00: 0%. De R$ 100,00 a R$ 499,99: 1%. A partir de R$ 500,00: 5%.
- A faixa é aplicada a cada venda, nunca ao total do vendedor.
- Cada comissão é arredondada com `ROUND_HALF_UP` para 2 casas antes de ser somada.
- Todos os cálculos usam `Decimal`. Os números do JSON são lidos pela representação textual, sem passar por erro de ponto flutuante.
- Vendas com mesmo vendedor e valor não são consideradas duplicadas, pois o JSON não tem identificador.
- Nomes de vendedor são comparados após remover espaços nas pontas.
- Valor zero é aceito (comissão zero). Vendedor vazio, valor negativo, ausente ou não numérico são rejeitados, com indicação do número do registro. Todos os erros do arquivo são listados.
- `data/vendas.json` contém o JSON do desafio. Com as três faixas acima, o resultado é: João Silva R$ 495,69, Maria Souza R$ 465,96, Carlos Oliveira R$ 379,38, Ana Lima R$ 404,99 e total geral R$ 1.746,02. O teste `test_json_do_desafio_gera_resultados_esperados` confere esses valores.
- O enunciado do desafio cita apenas as faixas de 1% (abaixo de R$ 500,00) e 5% (a partir de R$ 500,00). Foi mantida a faixa adicional de 0% abaixo de R$ 100,00, pois só com ela os totais esperados são obtidos (sem ela, o total geral seria R$ 1.747,68).

**Estoque**
- O estoque inicial vem de `data/estoque.json` e é carregado apenas quando a tabela de produtos está vazia (primeira inicialização do banco).
- Cada movimentação atualiza o estoque e grava o histórico na mesma transação (`BEGIN IMMEDIATE` / `COMMIT` / `ROLLBACK`).
- O identificador é `INTEGER PRIMARY KEY AUTOINCREMENT`.
- Rejeitadas: quantidade menor ou igual a zero, saída maior que o saldo, descrição vazia e produto inexistente.
- Para recomeçar do zero, apague `data/gestor.db`.

**Juros**
- Juros simples de 2,5% ao dia sobre o valor original, em dias corridos completos.
- `juros = valor * 0,025 * dias`. Vencimento hoje ou futuro resulta em juros zero.
- A data de cálculo é a data do sistema (`date.today()`).
- Não há multa nem juros mensais. O resultado é arredondado para 2 casas com `ROUND_HALF_UP`.
