# ChamaAí — Registro de Testes

## 1. Objetivo
Registrar os testes realizados no sistema ChamaAí, incluindo os testes automatizados e os testes de interface.

## 2. Ambiente de testes
- Linguagem: Python
- Framework web: Flask
- Banco de dados: SQLite
- Testes automatizados: pytest
- Testes de interface: Selenium
- Navegador: Google Chrome
- Controle de versão: Git

## 3. Resultados dos testes

| ID | Teste | Resultado | Status |
|---|---|---|---|
| T01 | Listagem de categorias | Teste automatizado aprovado | Aprovado |
| T02 | Cadastro de categoria | Teste automatizado aprovado | Aprovado |
| T03 | Validação de campos obrigatórios | Teste automatizado aprovado | Aprovado |
| T04 | Consulta, edição e desativação de categoria | Testes automatizados aprovados | Aprovado |
| T05 | Prevenção de categorias duplicadas | Teste automatizado aprovado | Aprovado |
| T06 | Prevenção de prestadores duplicados | Teste automatizado aprovado | Aprovado |
| T07 | Cadastro de categoria pelo navegador | Teste Selenium aprovado | Aprovado |

## 4. Defeitos
Até o momento, não foram relatados defeitos confirmados nos testes executados. Novos defeitos deverão ser registrados quando forem identificados e reproduzidos.

## 5. Observações
O conjunto de testes automatizados dos CRUDs apresentou 11 testes aprovados. O teste de interface com Selenium apresentou 1 teste aprovado, executado em aproximadamente 44 segundos.

## 6. Próximas atividades
- Verificar o registro de defeitos em uma ferramenta de rastreamento.
- Atualizar o cronograma com as datas e durações reais.
- Preparar o relatório de status do projeto.

### Testes do RF31 — Ativação e desativação de categorias

**Data de execução:** 28/10/2026  
**Arquivo de testes:** `tests/test_crud.py`  
**Ferramenta:** pytest

**Resultado:** 15 testes passaram.

**Comportamentos verificados:**
- Desativação de categoria;
- Reativação de categoria;
- Prevenção de desativação repetida;
- Prevenção de ativação repetida;
- Tratamento de categoria inexistente.

**Conclusão:** os testes automatizados executados passaram. O controle de acesso administrativo permanece pendente de implementação e validação.
