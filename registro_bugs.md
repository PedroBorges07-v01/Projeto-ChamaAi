# ChamaAí — Registro de defeitos (Release 02)

Não há, neste projeto, servidor, URL ou credencial de Mantis ou Bugzilla. Os defeitos reproduzidos nesta continuidade foram registrados aqui, no formato pedido pela disciplina.

## BUG-01 — O primeiro botão de envio da página encerra a sessão

- **Prioridade:** alta
- **Situação:** corrigido
- **Onde:** `templates/base.html` (botão Sair) e `tests/test_selenium.py`
- **Descrição:** Com o usuário autenticado, o botão Sair é um `button type="submit"` no topo do HTML. A suíte Selenium acionava o primeiro botão de envio da página ao cadastrar uma categoria. O navegador enviava `POST /logout` em vez de salvar a categoria.
- **Resultado esperado:** o formulário da categoria é enviado e a categoria aparece na listagem.
- **Resultado obtido:** redirecionamento para `/login` e mensagem de saída da conta. O teste `test_cadastrar_categoria_no_navegador` excedeu o tempo de espera em 04/11/2026.
- **Etapas para reprodução:**
  1. Entrar como administrador.
  2. Abrir `/categorias/nova`.
  3. Acionar o primeiro `button[type=submit]` do documento, sem restringir o seletor ao formulário principal.
- **Correção:** os testes passaram a usar o seletor `main form button[type=submit]`.

## BUG-02 — Navegação imediata cancelava o cadastro no teste

- **Prioridade:** média
- **Situação:** corrigido
- **Onde:** `tests/test_selenium.py`
- **Descrição:** Depois do clique em Salvar, alguns testes abriam outra URL antes de o envio terminar. O carregamento da página seguinte cancelava o `POST`. A listagem abria sem o registro recém-criado e o teste falhava por tempo esgotado.
- **Resultado esperado:** aguardar a confirmação do cadastro e só então abrir a listagem.
- **Resultado obtido:** em 04/11/2026, `test_desativar_categoria`, `test_impedir_desativar_categoria_inativa_novamente` e `test_impedir_prestador_duplicado` falharam. O log do servidor mostrou `GET` da listagem sem o `POST` correspondente, ou a busca do campo nome na listagem.
- **Etapas para reprodução:**
  1. Preencher um formulário de categoria ou prestador no Selenium.
  2. Clicar em Salvar e, no comando seguinte, chamar `driver.get` de outra rota sem esperar a resposta.
- **Correção:** os testes aguardam a mensagem de sucesso ou o nome cadastrado antes de navegar.

## Execução que evidenciou os defeitos

- **Data:** 04/11/2026
- **Comando:** `pytest tests/test_selenium.py --tb=line`
- **Antes da correção:** 20 aprovados e 5 reprovados.
- **Depois da correção, no mesmo dia:** `pytest tests/test_selenium.py tests/test_crud.py` — 33 aprovados, 0 reprovados, 56,88 s.
