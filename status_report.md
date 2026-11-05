# STATUS REPORT — Projeto ChamaAí

**Projeto:** ChamaAí — Marketplace de Serviços  
**Marco:** Release 02  
**Data do relatório:** 04/11/2026  
**Responsável indicado no relatório anterior:** Pedro Henrique Borges  
**Versão do relatório:** 2.0  
**Relatório anterior:** 27/10/2026, versão 1.0

## 1. Introdução e revisão de marco

A Release 01 entregou os CRUDs de categorias e prestadores, login inicial e um cadastro público de cliente. O relatório de 27/10/2026 registrava 11 testes pytest e 1 teste Selenium aprovados. Em 28/10/2026, o arquivo `registro_testes.md` registrou 15 testes pytest, com controle de acesso administrativo ainda pendente.

A Release 02 mantém a mesma aplicação Flask e o mesmo SQLite. Foram acrescentados o CRUD de clientes, o CRUD de serviços oferecidos, painéis por perfil, solicitações e a restrição das operações administrativas.

## 2. Itens revisados

### Cronograma

O cronograma da Release 01 não tinha datas de início e fim. As únicas datas já escritas no projeto são 27/10/2026 (status report) e 28/10/2026 (testes do RF31). As atividades da Release 02 executadas nesta continuidade estão datadas em 04/11/2026. Não há medição de horas.

### Orçamento

Não há orçamento, custo real nem custo orçado nos arquivos do projeto. Não é possível comparar previsto e realizado.

### Recursos humanos

O único nome registrado é Pedro Henrique Borges, como responsável do relatório de 27/10/2026. Não há alocação, carga horária nem equipe adicional documentada.

### Comunicação

Os registros existentes são `cronograma.md`, `registro_testes.md`, `registro_bugs.md` e este status report. Não há ata, canal ou ferramenta de comunicação configurada no repositório.

### Riscos

- A baseline Git citada em 27/10/2026 (`baseline-v1.0`) não estava presente no diretório auditado em 04/11/2026.
- Não existe instância de Mantis ou Bugzilla no projeto.
- Os indicadores de valor agregado não podem ser calculados sem orçamento e sem percentuais planejados.
- A senha de administrador de desenvolvimento não está versionada. O comando `flask criar-admin` continua sendo o meio de criar essa conta no banco local.

## 3. Acompanhamento de ações corretivas

| Ação vinda da Release 01 | Situação em 04/11/2026 |
|---|---|
| Preencher datas reais do cronograma | Parcial. Entraram só as datas que já existiam e a data desta execução. Horas continuam não medidas. |
| Configurar ferramenta de defeitos | Não havia servidor. Os dois defeitos reproduzidos foram registrados em `registro_bugs.md`. |
| Ampliar testes de interface | Concluída nesta execução: 25 testes Selenium e 8 testes de CRUD/permissão. |
| Confirmar a baseline | A tag antiga não foi encontrada. A baseline da Release 02 é a tag criada neste fechamento, se o commit for aceito pelo repositório. |
| Controle de acesso administrativo | Concluída. Cliente e prestador não gerenciam o CRUD administrativo. |

Defeitos corrigidos nesta continuidade: BUG-01 e BUG-02, descritos em `registro_bugs.md`. Ambos apareceram na primeira execução Selenium de 04/11/2026 (20 aprovados, 5 reprovados) e deixaram de falhar na execução seguinte.

## 4. Pendências do período

- Publicar os defeitos em Mantis ou Bugzilla quando a disciplina informar a ferramenta e o acesso.
- Recuperar ou reconstruir o histórico Git da Release 01, se ele existir em outro computador. Neste diretório ele não estava.
- Informar orçamento, valor planejado e valor agregado para calcular SPI, CPI, TAC e EAC.
- Medir a duração real das atividades.

## 5. Parecer sobre o projeto

O marco funcional da Release 02 está implementado na aplicação existente: quatro CRUDs com persistência SQLite, três perfis, login e bloqueio de rotas. A verificação desta data foi a suíte automatizada, não uma declaração sem execução.

O parecer de gerenciamento é parcial. O produto avançou; a linha de base de custo e o histórico Git anterior não estão disponíveis para auditoria.

## 6. Pontos de sucesso e pontos de atenção

**Sucesso**

- CRUDs de clientes, prestadores, serviços e categorias operando sobre o banco real.
- Login direciona cliente, prestador e administrador ao painel do próprio perfil.
- Em 04/11/2026, 33 testes passaram depois das correções (8 de CRUD/permissão e 25 Selenium).

**Atenção**

- Sem Mantis/Bugzilla acessível, o rastreamento externo continua pendente.
- Sem orçamento, os índices de valor agregado ficam sem cálculo.
- A primeira execução Selenium reprovou 5 testes. A causa foi corrigida, mas mostra que a suíte depende de seletores específicos por causa do botão Sair.

## 7. Análise de valor agregado

Não há, no projeto, BAC, PV, EV ou AC. Por isso os índices abaixo não foram estimados.

| Indicador | Fórmula usada na disciplina | Resultado |
|---|---|---|
| SPI | EV / PV | Não calculado. PV e EV ausentes. |
| CPI | EV / AC | Não calculado. EV e AC ausentes. |
| TAC | Tempo previsto / SPI, quando aplicável | Não calculado. Não há duração prevista nem SPI. |
| EAC | BAC / CPI, quando aplicável | Não calculado. Não há BAC nem CPI. |

## 8. Verificação executada em 04/11/2026

Comando final, no ambiente `venv` do projeto:

`pytest tests/test_selenium.py tests/test_crud.py --tb=line`

Resultado: 33 aprovados, 0 reprovados, 56,88 segundos.

A execução anterior, só da suíte Selenium, teve 20 aprovados e 5 reprovados. Esses 5 casos estão no registro de bugs.
