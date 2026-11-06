import uuid

from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from tests.conftest import (
    EMAIL_ADMIN,
    EMAIL_CLIENTE,
    EMAIL_PRESTADOR,
    SENHA_ADMIN,
    SENHA_CLIENTE,
    SENHA_PRESTADOR,
)


def entrar(navegador, url_base, email, senha):
    espera = WebDriverWait(navegador, 10)
    navegador.get(f"{url_base}/login")
    espera.until(EC.visibility_of_element_located((By.NAME, "email"))).send_keys(email)
    navegador.find_element(By.NAME, "senha").send_keys(senha)
    navegador.find_element(By.CSS_SELECTOR, "main form button[type='submit']").click()
    espera.until(EC.url_contains("/painel"))
    assert "Login realizado com sucesso" in navegador.page_source


def test_listar_categorias(navegador, url_base):
    navegador.get(f"{url_base}/categorias")
    espera = WebDriverWait(navegador, 10)
    espera.until(EC.presence_of_element_located((By.TAG_NAME, "body")))
    assert "Categorias" in navegador.page_source


def test_proteger_cadastro_de_categoria(navegador, url_base):
    navegador.get(f"{url_base}/categorias/nova")
    espera = WebDriverWait(navegador, 10)
    espera.until(EC.url_contains("/login"))
    assert "Entrar no ChamaAí" in navegador.page_source


def test_cadastrar_categoria_no_navegador(navegador, url_base):
    entrar(navegador, url_base, EMAIL_ADMIN, SENHA_ADMIN)
    espera = WebDriverWait(navegador, 10)
    nome_categoria = f"Teste Selenium {uuid.uuid4().hex[:6]}"
    navegador.get(f"{url_base}/categorias/nova")
    campo_nome = espera.until(EC.visibility_of_element_located((By.ID, "nome")))
    campo_nome.send_keys(nome_categoria)
    navegador.find_element(By.NAME, "descricao").send_keys(
        "Categoria criada automaticamente pelo Selenium"
    )
    navegador.find_element(By.CSS_SELECTOR, "main form button[type='submit']").click()
    espera.until(
        EC.presence_of_element_located(
            (By.XPATH, f"//*[contains(text(), '{nome_categoria}')]")
        )
    )
    assert nome_categoria in navegador.page_source


def test_impedir_categoria_sem_nome(navegador, url_base):
    entrar(navegador, url_base, EMAIL_ADMIN, SENHA_ADMIN)
    espera = WebDriverWait(navegador, 10)
    navegador.get(f"{url_base}/categorias/nova")
    navegador.find_element(By.NAME, "descricao").send_keys("Categoria sem nome para teste")
    navegador.find_element(By.CSS_SELECTOR, "main form button[type='submit']").click()
    espera.until(EC.visibility_of_element_located((By.ID, "nome")))
    assert navegador.current_url.endswith("/categorias/nova")


def test_editar_categoria(navegador, url_base):
    entrar(navegador, url_base, EMAIL_ADMIN, SENHA_ADMIN)
    espera = WebDriverWait(navegador, 10)
    nome_original = f"Categoria Original {uuid.uuid4().hex[:6]}"
    nome_novo = f"Categoria Editada {uuid.uuid4().hex[:6]}"
    navegador.get(f"{url_base}/categorias/nova")
    navegador.find_element(By.ID, "nome").send_keys(nome_original)
    navegador.find_element(By.NAME, "descricao").send_keys("Descrição original")
    navegador.find_element(By.CSS_SELECTOR, "main form button[type='submit']").click()
    espera.until(
        EC.presence_of_element_located(
            (By.XPATH, f"//*[contains(text(), '{nome_original}')]")
        )
    )
    navegador.get(f"{url_base}/categorias")
    link_editar = espera.until(
        EC.element_to_be_clickable(
            (
                By.XPATH,
                f"//*[contains(text(), '{nome_original}')]/ancestor::*[self::tr or self::div][1]//a[contains(@href, '/editar')]",
            )
        )
    )
    link_editar.click()
    campo_nome = espera.until(EC.visibility_of_element_located((By.ID, "nome")))
    campo_nome.clear()
    campo_nome.send_keys(nome_novo)
    navegador.find_element(By.CSS_SELECTOR, "main form button[type='submit']").click()
    espera.until(
        EC.presence_of_element_located(
            (By.XPATH, f"//*[contains(text(), '{nome_novo}')]")
        )
    )
    assert nome_novo in navegador.page_source


def test_desativar_categoria(navegador, url_base):
    entrar(navegador, url_base, EMAIL_ADMIN, SENHA_ADMIN)
    espera = WebDriverWait(navegador, 10)
    nome_categoria = f"Categoria Desativar {uuid.uuid4().hex[:6]}"
    navegador.get(f"{url_base}/categorias/nova")
    navegador.find_element(By.ID, "nome").send_keys(nome_categoria)
    navegador.find_element(By.NAME, "descricao").send_keys(
        "Categoria criada para testar desativação"
    )
    navegador.find_element(By.CSS_SELECTOR, "main form button[type='submit']").click()
    espera.until(EC.text_to_be_present_in_element((By.TAG_NAME, "body"), nome_categoria))
    navegador.get(f"{url_base}/categorias")
    linha = espera.until(
        EC.presence_of_element_located(
            (By.XPATH, f"//tr[td[contains(., '{nome_categoria}')]]")
        )
    )
    navegador.execute_script("window.confirm = () => true;")
    linha.find_element(By.XPATH, ".//button[normalize-space()='Desativar']").click()
    espera.until(EC.staleness_of(linha))
    linha_atualizada = espera.until(
        EC.presence_of_element_located(
            (By.XPATH, f"//tr[td[contains(., '{nome_categoria}')]]")
        )
    )
    espera.until(lambda _: "Inativa" in linha_atualizada.text)


def test_reativar_categoria(navegador, url_base):
    entrar(navegador, url_base, EMAIL_ADMIN, SENHA_ADMIN)
    espera = WebDriverWait(navegador, 10)
    nome_categoria = f"Categoria Reativar {uuid.uuid4().hex[:6]}"
    navegador.get(f"{url_base}/categorias/nova")
    navegador.find_element(By.ID, "nome").send_keys(nome_categoria)
    navegador.find_element(By.NAME, "descricao").send_keys(
        "Categoria criada para testar reativação"
    )
    navegador.find_element(By.CSS_SELECTOR, "main form button[type='submit']").click()
    espera.until(EC.text_to_be_present_in_element((By.TAG_NAME, "body"), nome_categoria))
    navegador.get(f"{url_base}/categorias")
    linha = espera.until(
        EC.presence_of_element_located(
            (By.XPATH, f"//tr[td[contains(., '{nome_categoria}')]]")
        )
    )
    navegador.execute_script("window.confirm = () => true;")
    linha.find_element(By.XPATH, ".//button[normalize-space()='Desativar']").click()
    espera.until(
        EC.text_to_be_present_in_element(
            (By.XPATH, f"//tr[td[contains(., '{nome_categoria}')]]"),
            "Inativa",
        )
    )
    linha = navegador.find_element(
        By.XPATH, f"//tr[td[contains(., '{nome_categoria}')]]"
    )
    navegador.execute_script("window.confirm = () => true;")
    linha.find_element(By.XPATH, ".//button[normalize-space()='Ativar']").click()
    espera.until(
        EC.text_to_be_present_in_element(
            (By.XPATH, f"//tr[td[contains(., '{nome_categoria}')]]"),
            "Ativa",
        )
    )
    linha_atualizada = navegador.find_element(
        By.XPATH, f"//tr[td[contains(., '{nome_categoria}')]]"
    )
    assert "Ativa" in linha_atualizada.text
    assert linha_atualizada.find_elements(
        By.XPATH, ".//button[normalize-space()='Desativar']"
    )


def test_impedir_categoria_duplicada(navegador, url_base):
    entrar(navegador, url_base, EMAIL_ADMIN, SENHA_ADMIN)
    espera = WebDriverWait(navegador, 10)
    nome_categoria = f"Categoria Duplicada {uuid.uuid4().hex[:6]}"
    descricao = "Instalacoes"
    navegador.get(f"{url_base}/categorias/nova")
    navegador.find_element(By.ID, "nome").send_keys(nome_categoria)
    navegador.find_element(By.NAME, "descricao").send_keys(descricao)
    navegador.find_element(By.CSS_SELECTOR, "main form button[type='submit']").click()
    espera.until(EC.text_to_be_present_in_element((By.TAG_NAME, "body"), nome_categoria))
    navegador.get(f"{url_base}/categorias/nova")
    navegador.find_element(By.ID, "nome").send_keys(nome_categoria)
    navegador.find_element(By.NAME, "descricao").send_keys(descricao)
    navegador.find_element(By.CSS_SELECTOR, "main form button[type='submit']").click()
    espera.until(
        EC.text_to_be_present_in_element((By.TAG_NAME, "body"), "Já existe uma categoria")
    )
    assert "Já existe uma categoria" in navegador.find_element(By.TAG_NAME, "body").text


def test_cadastrar_prestador(navegador, url_base):
    espera = WebDriverWait(navegador, 10)
    nome_prestador = f"Prestador Teste {uuid.uuid4().hex[:6]}"
    cpf = f"111.{uuid.uuid4().hex[:3]}.{uuid.uuid4().hex[:3]}-44"
    navegador.get(f"{url_base}/prestadores/novo")
    navegador.find_element(By.NAME, "nome").send_keys(nome_prestador)
    navegador.find_element(By.NAME, "cpf").send_keys(cpf)
    navegador.find_element(By.NAME, "email").send_keys(
        f"{uuid.uuid4().hex[:8]}@example.com"
    )
    navegador.find_element(By.NAME, "senha").send_keys("SenhaTeste123!")
    navegador.find_element(By.NAME, "telefone").send_keys("31999999999")
    navegador.find_element(By.NAME, "especialidade").send_keys("Eletrica")
    navegador.find_element(By.CSS_SELECTOR, "main form button[type='submit']").click()
    espera.until(
        EC.text_to_be_present_in_element((By.TAG_NAME, "body"), nome_prestador)
    )
    assert nome_prestador in navegador.find_element(By.TAG_NAME, "body").text


def test_impedir_prestador_duplicado(navegador, url_base):
    espera = WebDriverWait(navegador, 10)
    cpf_duplicado = f"222.{uuid.uuid4().hex[:3]}.{uuid.uuid4().hex[:3]}-55"
    navegador.get(f"{url_base}/prestadores/novo")
    navegador.find_element(By.NAME, "nome").send_keys("Prestador Original")
    navegador.find_element(By.NAME, "cpf").send_keys(cpf_duplicado)
    navegador.find_element(By.NAME, "email").send_keys(
        f"{uuid.uuid4().hex[:8]}@example.com"
    )
    navegador.find_element(By.NAME, "senha").send_keys("SenhaTeste123!")
    navegador.find_element(By.NAME, "telefone").send_keys("")
    navegador.find_element(By.NAME, "especialidade").send_keys("Pintura")
    navegador.find_element(By.CSS_SELECTOR, "main form button[type='submit']").click()
    espera.until(
        EC.text_to_be_present_in_element((By.TAG_NAME, "body"), "Prestador cadastrado com sucesso")
    )
    navegador.get(f"{url_base}/prestadores/novo")
    navegador.find_element(By.NAME, "nome").send_keys("Outro Prestador")
    navegador.find_element(By.NAME, "cpf").send_keys(cpf_duplicado)
    navegador.find_element(By.NAME, "email").send_keys(
        f"{uuid.uuid4().hex[:8]}@example.com"
    )
    navegador.find_element(By.NAME, "senha").send_keys("SenhaTeste123!")
    navegador.find_element(By.NAME, "telefone").send_keys("")
    navegador.find_element(By.NAME, "especialidade").send_keys("Pintura")
    navegador.find_element(By.CSS_SELECTOR, "main form button[type='submit']").click()
    espera.until(
        EC.text_to_be_present_in_element((By.TAG_NAME, "body"), "Já existe um prestador")
    )
    assert "Já existe um prestador" in navegador.find_element(By.TAG_NAME, "body").text


def test_impedir_prestador_sem_nome(navegador, url_base):
    navegador.get(f"{url_base}/prestadores/novo")
    navegador.find_element(By.NAME, "cpf").send_keys(
        f"333.{uuid.uuid4().hex[:3]}.{uuid.uuid4().hex[:3]}-66"
    )
    navegador.find_element(By.NAME, "email").send_keys(
        f"{uuid.uuid4().hex[:8]}@example.com"
    )
    navegador.find_element(By.CSS_SELECTOR, "main form button[type='submit']").click()
    campo_nome = navegador.find_element(By.NAME, "nome")
    assert campo_nome.get_attribute("required") is not None
    assert navegador.current_url.endswith("/prestadores/novo")


def test_listar_prestadores(navegador, url_base):
    espera = WebDriverWait(navegador, 10)
    navegador.get(f"{url_base}/prestadores")
    espera.until(
        EC.text_to_be_present_in_element((By.TAG_NAME, "body"), "Prestadores de servi")
    )
    assert "Prestadores de servi" in navegador.find_element(By.TAG_NAME, "body").text


def test_consultar_categoria(navegador, url_base):
    entrar(navegador, url_base, EMAIL_ADMIN, SENHA_ADMIN)
    espera = WebDriverWait(navegador, 10)
    nome_categoria = f"Categoria Consulta {uuid.uuid4().hex[:6]}"
    navegador.get(f"{url_base}/categorias/nova")
    navegador.find_element(By.ID, "nome").send_keys(nome_categoria)
    navegador.find_element(By.NAME, "descricao").send_keys(
        "Categoria criada para testar a consulta"
    )
    navegador.find_element(By.CSS_SELECTOR, "main form button[type='submit']").click()
    espera.until(EC.text_to_be_present_in_element((By.TAG_NAME, "body"), nome_categoria))
    navegador.get(f"{url_base}/categorias")
    linha = espera.until(
        EC.presence_of_element_located(
            (By.XPATH, f"//tr[td[contains(., '{nome_categoria}')]]")
        )
    )
    assert nome_categoria in linha.text


def test_impedir_desativar_categoria_inativa_novamente(navegador, url_base):
    entrar(navegador, url_base, EMAIL_ADMIN, SENHA_ADMIN)
    espera = WebDriverWait(navegador, 10)
    nome_categoria = f"Categoria Inativa {uuid.uuid4().hex[:6]}"
    navegador.get(f"{url_base}/categorias/nova")
    navegador.find_element(By.ID, "nome").send_keys(nome_categoria)
    navegador.find_element(By.NAME, "descricao").send_keys("Teste de desativacao repetida")
    navegador.find_element(By.CSS_SELECTOR, "main form button[type='submit']").click()
    espera.until(EC.text_to_be_present_in_element((By.TAG_NAME, "body"), nome_categoria))
    navegador.get(f"{url_base}/categorias")
    linha = espera.until(
        EC.presence_of_element_located(
            (By.XPATH, f"//tr[td[contains(., '{nome_categoria}')]]")
        )
    )
    navegador.execute_script("window.confirm = () => true;")
    linha.find_element(By.XPATH, ".//button[contains(., 'Desativar')]").click()
    espera.until(EC.text_to_be_present_in_element((By.TAG_NAME, "body"), nome_categoria))
    navegador.get(f"{url_base}/categorias")
    linha = espera.until(
        EC.presence_of_element_located(
            (By.XPATH, f"//tr[td[contains(., '{nome_categoria}')]]")
        )
    )
    assert "Ativar" in linha.text


def test_impedir_reativar_categoria_ativa_novamente(navegador, url_base):
    entrar(navegador, url_base, EMAIL_ADMIN, SENHA_ADMIN)
    espera = WebDriverWait(navegador, 10)
    nome_categoria = f"Categoria Ativa {uuid.uuid4().hex[:6]}"
    navegador.get(f"{url_base}/categorias/nova")
    navegador.find_element(By.ID, "nome").send_keys(nome_categoria)
    navegador.find_element(By.NAME, "descricao").send_keys("Teste de ativacao repetida")
    navegador.find_element(By.CSS_SELECTOR, "main form button[type='submit']").click()
    espera.until(EC.text_to_be_present_in_element((By.TAG_NAME, "body"), nome_categoria))
    navegador.get(f"{url_base}/categorias")
    linha = espera.until(
        EC.presence_of_element_located(
            (By.XPATH, f"//tr[td[contains(., '{nome_categoria}')]]")
        )
    )
    assert "Desativar" in linha.text
    assert "Ativar" not in linha.text


def test_ativar_categoria_inexistente(navegador, url_base):
    entrar(navegador, url_base, EMAIL_ADMIN, SENHA_ADMIN)
    resultado = navegador.execute_async_script(
        """
        const callback = arguments[arguments.length - 1];
        fetch('/categorias/999999/ativar', {
            method: 'POST',
            headers: {'Content-Type': 'application/x-www-form-urlencoded'},
            body: ''
        })
        .then(async resposta => ({status: resposta.status, texto: await resposta.text()}))
        .then(callback)
        .catch(erro => callback({erro: erro.toString()}));
        """
    )
    assert "erro" not in resultado
    assert resultado["status"] == 200
    assert "Categoria não encontrada." in resultado["texto"]


def test_consultar_prestador_com_servicos(navegador, url_base):
    entrar(navegador, url_base, EMAIL_ADMIN, SENHA_ADMIN)
    espera = WebDriverWait(navegador, 10)
    sufixo = uuid.uuid4().hex[:6]
    nome_categoria = f"Categoria Prestador {sufixo}"
    nome_prestador = f"Prestador Consulta {sufixo}"
    cpf = f"111.{uuid.uuid4().hex[:3]}.{uuid.uuid4().hex[:3]}-44"
    email = f"prestador-{sufixo}@example.com"
    navegador.get(f"{url_base}/categorias/nova")
    navegador.find_element(By.ID, "nome").send_keys(nome_categoria)
    navegador.find_element(By.NAME, "descricao").send_keys(
        "Categoria para teste de consulta do prestador"
    )
    navegador.find_element(By.CSS_SELECTOR, "main form button[type='submit']").click()
    espera.until(EC.url_contains("/categorias"))
    espera.until(EC.text_to_be_present_in_element((By.TAG_NAME, "body"), nome_categoria))
    navegador.get(f"{url_base}/prestadores/novo")
    espera.until(EC.presence_of_element_located((By.NAME, "nome")))
    navegador.find_element(By.NAME, "nome").send_keys(nome_prestador)
    navegador.find_element(By.NAME, "cpf").send_keys(cpf)
    navegador.find_element(By.NAME, "email").send_keys(email)
    navegador.find_element(By.NAME, "senha").send_keys("SenhaTeste123!")
    checkbox = espera.until(
        EC.element_to_be_clickable(
            (
                By.XPATH,
                f"//label[contains(., '{nome_categoria}')]/input[@name='categorias']",
            )
        )
    )
    checkbox.click()
    navegador.find_element(By.CSS_SELECTOR, "main form button[type='submit']").click()
    espera.until(EC.text_to_be_present_in_element((By.TAG_NAME, "body"), nome_prestador))
    navegador.get(f"{url_base}/prestadores")
    linha = espera.until(
        EC.presence_of_element_located(
            (By.XPATH, f"//tr[td[contains(., '{nome_prestador}')]]")
        )
    )
    linha.find_element(By.XPATH, ".//a[contains(., 'Consultar')]").click()
    espera.until(EC.text_to_be_present_in_element((By.TAG_NAME, "body"), nome_categoria))
    texto_pagina = navegador.find_element(By.TAG_NAME, "body").text
    assert nome_prestador in texto_pagina
    assert nome_categoria in texto_pagina


def test_cadastrar_cliente(navegador, url_base):
    email = f"cliente-{uuid.uuid4().hex[:8]}@example.com"
    navegador.get(f"{url_base}/clientes/novo")
    navegador.find_element(By.NAME, "nome").send_keys("Cliente Teste")
    navegador.find_element(By.NAME, "email").send_keys(email)
    navegador.find_element(By.NAME, "senha").send_keys("SenhaTeste123!")
    navegador.find_element(By.CSS_SELECTOR, "main form button[type='submit']").click()
    espera = WebDriverWait(navegador, 10)
    espera.until(EC.url_contains("/login"))
    assert "Cadastro realizado com sucesso" in navegador.page_source


def test_impedir_cliente_sem_nome(navegador, url_base):
    email = f"cliente-{uuid.uuid4().hex[:8]}@example.com"
    navegador.get(f"{url_base}/clientes/novo")
    navegador.find_element(By.NAME, "email").send_keys(email)
    navegador.find_element(By.NAME, "senha").send_keys("SenhaTeste123!")
    campo_nome = navegador.find_element(By.NAME, "nome")
    assert campo_nome.get_attribute("required") is not None


def test_impedir_cliente_com_senha_curta(navegador, url_base):
    email = f"cliente-{uuid.uuid4().hex[:8]}@example.com"
    navegador.get(f"{url_base}/clientes/novo")
    navegador.find_element(By.NAME, "nome").send_keys("Cliente Teste")
    navegador.find_element(By.NAME, "email").send_keys(email)
    navegador.find_element(By.NAME, "senha").send_keys("123")
    navegador.execute_script(
        "document.querySelector('form').setAttribute('novalidate', 'novalidate')"
    )
    navegador.find_element(By.CSS_SELECTOR, "main form button[type='submit']").click()
    espera = WebDriverWait(navegador, 10)
    espera.until(
        EC.text_to_be_present_in_element(
            (By.TAG_NAME, "body"),
            "A senha deve ter pelo menos 8 caracteres.",
        )
    )
    assert "A senha deve ter pelo menos 8 caracteres." in navegador.page_source


def test_impedir_cliente_com_email_duplicado(navegador, url_base):
    email = f"cliente-{uuid.uuid4().hex[:8]}@example.com"
    navegador.get(f"{url_base}/clientes/novo")
    for nome in ["Cliente Um", "Cliente Dois"]:
        navegador.find_element(By.NAME, "nome").clear()
        navegador.find_element(By.NAME, "nome").send_keys(nome)
        campo_email = navegador.find_element(By.NAME, "email")
        campo_email.clear()
        campo_email.send_keys(email)
        campo_senha = navegador.find_element(By.NAME, "senha")
        campo_senha.clear()
        campo_senha.send_keys("SenhaTeste123!")
        navegador.find_element(By.CSS_SELECTOR, "main form button[type='submit']").click()
        espera = WebDriverWait(navegador, 10)
        if nome == "Cliente Um":
            espera.until(EC.url_contains("/login"))
            espera.until(
                EC.text_to_be_present_in_element(
                    (By.TAG_NAME, "body"),
                    "Cadastro realizado com sucesso",
                )
            )
            navegador.get(f"{url_base}/clientes/novo")
            espera.until(EC.visibility_of_element_located((By.NAME, "nome")))
        else:
            espera.until(
                EC.text_to_be_present_in_element(
                    (By.TAG_NAME, "body"),
                    "Este e-mail já está cadastrado.",
                )
            )
    assert "Este e-mail já está cadastrado." in navegador.page_source


def test_cliente_nao_acessa_admin(navegador, url_base):
    entrar(navegador, url_base, EMAIL_CLIENTE, SENHA_CLIENTE)
    navegador.get(f"{url_base}/clientes")
    espera = WebDriverWait(navegador, 10)
    espera.until(EC.presence_of_element_located((By.TAG_NAME, "body")))
    assert "Acesso restrito ao administrador" in navegador.page_source


def test_login_prestador_abre_painel(navegador, url_base):
    entrar(navegador, url_base, EMAIL_PRESTADOR, SENHA_PRESTADOR)
    assert "Painel prestador" in navegador.page_source


def test_admin_lista_e_desativa_cliente(navegador, url_base):
    entrar(navegador, url_base, EMAIL_ADMIN, SENHA_ADMIN)
    espera = WebDriverWait(navegador, 10)
    navegador.get(f"{url_base}/clientes")
    espera.until(EC.text_to_be_present_in_element((By.TAG_NAME, "body"), "Cliente Teste"))
    linha = navegador.find_element(By.XPATH, "//tr[td[contains(., 'cliente-teste@example.com')]]")
    navegador.execute_script("window.confirm = () => true;")
    linha.find_element(By.XPATH, ".//button[normalize-space()='Desativar']").click()
    espera.until(
        EC.text_to_be_present_in_element(
            (By.XPATH, "//tr[td[contains(., 'cliente-teste@example.com')]]"),
            "Inativo",
        )
    )
    linha = navegador.find_element(
        By.XPATH, "//tr[td[contains(., 'cliente-teste@example.com')]]"
    )
    navegador.execute_script("window.confirm = () => true;")
    linha.find_element(By.XPATH, ".//button[normalize-space()='Ativar']").click()
    espera.until(
        EC.text_to_be_present_in_element(
            (By.XPATH, "//tr[td[contains(., 'cliente-teste@example.com')]]"),
            "Ativo",
        )
    )