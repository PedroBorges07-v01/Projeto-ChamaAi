# STATUS REPORT — Projeto ChamaServiço

**Projeto:** ChamaServiço — Marketplace de Serviços  
**Data do relatório:** A preencher  
**Responsável:** A preencher  
**Período de referência:** A preencher  
**Versão do relatório:** 1.0

## 1. Resumo executivo

O projeto ChamaServiço tem como objetivo desenvolver uma aplicação web para gerenciar categorias de serviços e prestadores. A aplicação foi desenvolvida utilizando Python, Flask, SQLite, HTML e CSS.

Até a data deste relatório, os dois módulos CRUD — categorias e prestadores — foram implementados. Também foram desenvolvidos testes automatizados com pytest e um teste de interface utilizando Selenium e Google Chrome.

Os testes executados apresentaram resultados positivos. O projeto também possui controle de versão com Git, incluindo commits e uma tag para a baseline inicial.

## 2. Situação geral do projeto

| Área | Situação | Observação |
|---|---|---|
| Desenvolvimento | Concluído para os dois CRUDs | Funcionalidades implementadas e verificadas |
| Testes automatizados | Aprovado | 11 testes com pytest passaram |
| Teste de interface | Aprovado | 1 teste Selenium passou |
| Controle de versão | Em andamento contínuo | Repositório Git configurado e commits realizados |
| Baseline de configuração | Parcialmente documentada | Existe uma tag inicial; verificar se representa a versão final exigida |
| Registro de testes | Preparado | Arquivo `registro_testes.md` criado |
| Cronograma | Preparado | Arquivo `cronograma.md`; datas reais ainda precisam ser preenchidas |
| Registro de defeitos | Pendente | Ferramenta de rastreamento ainda não configurada |
| Relatório de status | Elaborado | Este documento |

## 3. Atividades realizadas

1. Preparação do ambiente de desenvolvimento em Python.
2. Implementação do banco de dados SQLite.
3. Desenvolvimento do CRUD de categorias.
4. Desenvolvimento do CRUD de prestadores.
5. Implementação de testes automatizados com pytest.
6. Execução dos testes automatizados, com 11 aprovações.
7. Instalação e configuração do Selenium.
8. Execução de teste de cadastro de categoria pelo Google Chrome, com aprovação.
9. Configuração do Git e criação de commits.
10. Preparação dos registros de testes e do cronograma.

## 4. Resultados dos testes

| Tipo de teste | Quantidade | Aprovados | Reprovados |
|---|---:|---:|---:|
| Testes automatizados com pytest | 11 | 11 | 0 |
| Testes de interface com Selenium | 1 | 1 | 0 |
| **Total** | **12** | **12** | **0** |

O teste Selenium verificou o cadastro de uma categoria pelo navegador e confirmou que o novo registro apareceu na página.

Os resultados acima representam os testes executados até o momento. Eles não garantem, isoladamente, a ausência de defeitos em todas as funcionalidades.

## 5. Gerenciamento de configuração

O projeto utiliza Git para controle de versão. Foram criados commits para a implementação inicial e para os testes automatizados.

Existe uma tag chamada `baseline-v1.0`, associada à baseline inicial do projeto. Como os testes e documentos foram adicionados posteriormente, deve-se confirmar se a baseline exigida pelo trabalho precisa ser atualizada para representar uma versão integrada mais recente.

## 6. Defeitos e problemas conhecidos

Até o momento, não foram relatados defeitos confirmados nos testes executados.

O registro de defeitos em uma ferramenta específica ainda está pendente. Caso sejam encontrados defeitos durante novos testes, eles deverão ser documentados com descrição, passos para reprodução, resultado esperado, resultado obtido e prioridade.

## 7. Riscos e pontos de atenção

- **Cobertura de testes:** os testes atuais não cobrem necessariamente todos os fluxos dos dois CRUDs.
- **Rastreamento de defeitos:** ainda é necessário definir e utilizar uma ferramenta de registro, conforme os requisitos da disciplina.
- **Cronograma:** as datas planejadas e reais precisam ser preenchidas e comparadas.
- **Baseline:** é necessário confirmar a versão que deverá ser identificada como baseline de configuração.
- **Documentação:** os registros precisam ser revisados e mantidos sincronizados com o estado real do projeto.

## 8. Próximas atividades

1. Completar e validar o cronograma com as datas reais.
2. Configurar uma ferramenta de rastreamento de defeitos, caso exigida.
3. Ampliar os testes de interface e validar outros fluxos relevantes.
4. Revisar a baseline de configuração e registrar a versão integrada.
5. Verificar o estado do Git e confirmar que todos os documentos estão versionados.
6. Revisar este relatório antes da entrega.

## 9. Conclusão

O projeto apresenta progresso consistente: os dois CRUDs estão implementados, os testes executados foram aprovados e o controle de versão está configurado.

As principais pendências estão relacionadas à finalização da documentação de gerenciamento, à validação do cronograma, ao registro de defeitos em ferramenta apropriada e à confirmação da baseline de configuração exigida pela disciplina.

**Status geral:** Desenvolvimento funcional implementado; documentação de gerenciamento em finalização.
