import uuid

import pytest
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC


URL_BASE = "http://127.0.0.1:5000"
EMAIL_ADMIN = "admin-teste@example.com"
SENHA_ADMIN = "SenhaTeste123!"


@pytest.fixture
def navegador():
    opcoes = webdriver.ChromeOptions()
    driver = webdriver.Chrome(options=opcoes)
    driver.implicitly_wait(0)

    yield driver

    driver.quit()


@pytest.fixture
def admin_logado(navegador):
    espera = WebDriverWait(navegador, 10)
    navegador.get(f"{URL_BASE}/login")

    espera.until(
        EC.visibility_of_element_located((By.NAME, "email"))
    ).send_keys(EMAIL_ADMIN)

    navegador.find_element(By.NAME, "senha").send_keys(SENHA_ADMIN)

    navegador.find_element(
        By.CSS_SELECTOR, "button[type='submit']"
    ).click()

    espera.until(EC.url_to_be(f"{URL_BASE}/"))

    assert "Login realizado com sucesso" in navegador.page_source

    return navegador


def test_listar_categorias(navegador):
    navegador.get(f"{URL_BASE}/categorias")

    espera = WebDriverWait(navegador, 10)
    espera.until(
        EC.presence_of_element_located((By.TAG_NAME, "body"))
    )

    assert "Categorias" in navegador.page_source


def test_cadastrar_categoria_no_navegador(admin_logado):
    navegador = admin_logado
    espera = WebDriverWait(navegador, 10)

    nome_categoria = f"Teste Selenium {uuid.uuid4().hex[:6]}"

    navegador.get(f"{URL_BASE}/categorias/nova")

    campo_nome = espera.until(
        EC.visibility_of_element_located((By.ID, "nome"))
    )
    campo_nome.send_keys(nome_categoria)

    navegador.find_element(By.NAME, "descricao").send_keys(
        "Categoria criada automaticamente pelo Selenium"
    )

    navegador.find_element(
        By.CSS_SELECTOR, "button[type='submit']"
    ).click()

    espera.until(
        EC.presence_of_element_located(
            (By.XPATH, f"//*[contains(text(), '{nome_categoria}')]")
        )
    )

    assert nome_categoria in navegador.page_source


def test_impedir_categoria_sem_nome(admin_logado):
    navegador = admin_logado
    espera = WebDriverWait(navegador, 10)

    navegador.get(f"{URL_BASE}/categorias/nova")

    navegador.find_element(
        By.NAME, "descricao"
    ).send_keys("Categoria sem nome para teste")

    navegador.find_element(
        By.CSS_SELECTOR, "button[type='submit']"
    ).click()

    espera.until(
        EC.visibility_of_element_located((By.ID, "nome"))
    )

    assert navegador.current_url.endswith("/categorias/nova")




def test_proteger_cadastro_de_categoria(navegador):
    navegador.get(f"{URL_BASE}/categorias/nova")



def test_editar_categoria(admin_logado):
    navegador = admin_logado
    espera = WebDriverWait(navegador, 10)
    nome_original = f"Categoria Original {uuid.uuid4().hex[:6]}"
    nome_novo = f"Categoria Editada {uuid.uuid4().hex[:6]}"

    navegador.get(f"{URL_BASE}/categorias/nova")
    navegador.find_element(By.ID, "nome").send_keys(nome_original)
    navegador.find_element(By.NAME, "descricao").send_keys(
        "Descrição original"
    )
    navegador.find_element(
        By.CSS_SELECTOR, "button[type='submit']"
    ).click()

    espera.until(
        EC.presence_of_element_located(
            (By.XPATH, f"//*[contains(text(), '{nome_original}')]")
        )
    )

    # Abre a edição da categoria criada
    navegador.get(f"{URL_BASE}/categorias")
    link_editar = espera.until(
        EC.element_to_be_clickable(
            (By.XPATH, f"//*[contains(text(), '{nome_original}')]/ancestor::*[self::tr or self::div][1]//a[contains(@href, '/editar')]")
        )
    )
    link_editar.click()

    campo_nome = espera.until(
        EC.visibility_of_element_located((By.ID, "nome"))
    )
    campo_nome.clear()
    campo_nome.send_keys(nome_novo)

    navegador.find_element(
        By.CSS_SELECTOR, "button[type='submit']"
    ).click()

    espera.until(
        EC.presence_of_element_located(
            (By.XPATH, f"//*[contains(text(), '{nome_novo}')]")
        )
    )
    assert nome_novo in navegador.page_source


def test_desativar_categoria(admin_logado):
    navegador = admin_logado
    espera = WebDriverWait(navegador, 10)
    nome_categoria = f"Categoria Desativar {uuid.uuid4().hex[:6]}"

    # Cria a categoria
    navegador.get(f"{URL_BASE}/categorias/nova")
    navegador.find_element(By.ID, "nome").send_keys(nome_categoria)
    navegador.find_element(By.NAME, "descricao").send_keys(
        "Categoria criada para testar desativação"
    )
    navegador.find_element(
        By.CSS_SELECTOR, "button[type='submit']"
    ).click()

    # Abre a listagem e localiza a linha da categoria
    navegador.get(f"{URL_BASE}/categorias")
    linha = espera.until(
        EC.presence_of_element_located(
            (By.XPATH, f"//tr[td[contains(., '{nome_categoria}')]]")
        )
    )

    # Clica em Desativar; aceita a confirmação JavaScript
    navegador.execute_script(
        "window.confirm = () => true;"
    )
    linha.find_element(
        By.XPATH, ".//button[normalize-space()='Desativar']"
    ).click()

    # Confirma que o status passou para Inativa
    espera.until(
        EC.text_to_be_present_in_element(
            (By.XPATH, f"//tr[td[contains(., '{nome_categoria}')]]"),
            "Inativa"
        )
    )

    linha_atualizada = navegador.find_element(
        By.XPATH, f"//tr[td[contains(., '{nome_categoria}')]]"
    )
    assert "Inativa" in linha_atualizada.text
    assert linha_atualizada.find_elements(
        By.XPATH, ".//button[normalize-space()='Ativar']"
    )


def test_reativar_categoria(admin_logado):
    navegador = admin_logado
    espera = WebDriverWait(navegador, 10)
    nome_categoria = f"Categoria Reativar {uuid.uuid4().hex[:6]}"

    # Cria a categoria
    navegador.get(f"{URL_BASE}/categorias/nova")
    navegador.find_element(By.ID, "nome").send_keys(nome_categoria)
    navegador.find_element(By.NAME, "descricao").send_keys(
        "Categoria criada para testar reativação"
    )
    navegador.find_element(
        By.CSS_SELECTOR, "button[type='submit']"
    ).click()

    navegador.get(f"{URL_BASE}/categorias")
    linha = espera.until(
        EC.presence_of_element_located(
            (By.XPATH, f"//tr[td[contains(., '{nome_categoria}')]]")
        )
    )

    # Desativa primeiro
    navegador.execute_script("window.confirm = () => true;")
    linha.find_element(
        By.XPATH, ".//button[normalize-space()='Desativar']"
    ).click()

    espera.until(
        EC.text_to_be_present_in_element(
            (By.XPATH, f"//tr[td[contains(., '{nome_categoria}')]]"),
            "Inativa"
        )
    )

    # Atualiza a referência da linha após a navegação
    linha = navegador.find_element(
        By.XPATH, f"//tr[td[contains(., '{nome_categoria}')]]"
    )

    # Aceita a confirmação de reativação
    navegador.execute_script("window.confirm = () => true;")

    # Reativa
    linha.find_element(
        By.XPATH, ".//button[normalize-space()='Ativar']"
    ).click()

    espera.until(
        EC.text_to_be_present_in_element(
            (By.XPATH, f"//tr[td[contains(., '{nome_categoria}')]]"),
            "Ativa"
        )
    )

    linha_atualizada = navegador.find_element(
        By.XPATH, f"//tr[td[contains(., '{nome_categoria}')]]"
    )
    assert "Ativa" in linha_atualizada.text
    assert linha_atualizada.find_elements(
        By.XPATH, ".//button[normalize-space()='Desativar']"
    )


def test_impedir_categoria_duplicada(admin_logado):
    navegador = admin_logado
    espera = WebDriverWait(navegador, 10)
    nome_categoria = f"Categoria Duplicada {uuid.uuid4().hex[:6]}"
    descricao = "Instalacoes"

    # Cadastra a categoria pela primeira vez
    navegador.get(f"{URL_BASE}/categorias/nova")
    navegador.find_element(By.ID, "nome").send_keys(nome_categoria)
    navegador.find_element(By.NAME, "descricao").send_keys(descricao)
    navegador.find_element(
        By.CSS_SELECTOR, "button[type='submit']"
    ).click()

    espera.until(
        EC.text_to_be_present_in_element(
            (By.TAG_NAME, "body"),
            nome_categoria
        )
    )

    # Tenta cadastrar a mesma categoria novamente
    navegador.get(f"{URL_BASE}/categorias/nova")
    navegador.find_element(By.ID, "nome").send_keys(nome_categoria)
    navegador.find_element(By.NAME, "descricao").send_keys(descricao)
    navegador.find_element(
        By.CSS_SELECTOR, "button[type='submit']"
    ).click()

    # Verifica a mensagem de categoria duplicada
    espera.until(
        EC.text_to_be_present_in_element(
            (By.TAG_NAME, "body"),
            "Já existe uma categoria"
        )
    )

    assert "Já existe uma categoria" in navegador.find_element(
        By.TAG_NAME, "body"
    ).text




def test_cadastrar_prestador(navegador):
    espera = WebDriverWait(navegador, 10)
    nome_prestador = f"Prestador Teste {uuid.uuid4().hex[:6]}"
    cpf = f"111.{uuid.uuid4().hex[:3]}.{uuid.uuid4().hex[:3]}-44"

    navegador.get(f"{URL_BASE}/prestadores/novo")

    navegador.find_element(By.NAME, "nome").send_keys(nome_prestador)
    navegador.find_element(By.NAME, "cpf").send_keys(cpf)
    navegador.find_element(By.NAME, "email").send_keys(
        f"{uuid.uuid4().hex[:8]}@example.com"
    )
    navegador.find_element(By.NAME, "senha").send_keys(
        "SenhaTeste123!"
    )
    navegador.find_element(By.NAME, "telefone").send_keys("31999999999")
    navegador.find_element(By.NAME, "especialidade").send_keys("Eletrica")

    navegador.find_element(
        By.CSS_SELECTOR, "button[type='submit']"
    ).click()

    espera.until(
        EC.text_to_be_present_in_element(
            (By.TAG_NAME, "body"),
            nome_prestador
        )
    )

    assert nome_prestador in navegador.find_element(
        By.TAG_NAME, "body"
    ).text



def test_impedir_prestador_duplicado(navegador):
    espera = WebDriverWait(navegador, 10)
    cpf_duplicado = f"222.{uuid.uuid4().hex[:3]}.{uuid.uuid4().hex[:3]}-55"

    # Cadastra o primeiro prestador
    navegador.get(f"{URL_BASE}/prestadores/novo")

    navegador.find_element(By.NAME, "nome").send_keys(
        "Prestador Original"
    )
    navegador.find_element(By.NAME, "cpf").send_keys(cpf_duplicado)
    navegador.find_element(By.NAME, "email").send_keys(
        f"{uuid.uuid4().hex[:8]}@example.com"
    )
    navegador.find_element(By.NAME, "senha").send_keys(
        "SenhaTeste123!"
    )
    navegador.find_element(By.NAME, "telefone").send_keys("")
    navegador.find_element(By.NAME, "especialidade").send_keys("Pintura")

    navegador.find_element(
        By.CSS_SELECTOR, "button[type='submit']"
    ).click()

    espera.until(
        lambda driver: driver.execute_script(
            "return document.readyState"
        ) == "complete"
    )

    print("URL após segunda tentativa:", navegador.current_url)
    print(
        "Página após segunda tentativa:",
        navegador.execute_script(
            "return document.body.innerText"
    )
)

    print("URL após cadastro:", navegador.current_url)
    print(
        "Página após cadastro:",
        navegador.execute_script(
            "return document.body.innerText"
    )
)
    # Tenta cadastrar outro prestador com o mesmo CPF
    navegador.get(f"{URL_BASE}/prestadores/novo")

    navegador.find_element(By.NAME, "nome").send_keys(
        "Outro Prestador"
    )
    navegador.find_element(By.NAME, "cpf").send_keys(cpf_duplicado)
    navegador.find_element(By.NAME, "email").send_keys(
        f"{uuid.uuid4().hex[:8]}@example.com"
    )
    navegador.find_element(By.NAME, "senha").send_keys(
        "SenhaTeste123!"
    )
    navegador.find_element(By.NAME, "telefone").send_keys("")
    navegador.find_element(By.NAME, "especialidade").send_keys("Pintura")

    navegador.find_element(
        By.CSS_SELECTOR, "button[type='submit']"
    ).click()

    espera.until(
        EC.text_to_be_present_in_element(
            (By.TAG_NAME, "body"),
            "Já existe um prestador"
        )
    )

    assert "Já existe um prestador" in navegador.find_element(
        By.TAG_NAME, "body"
    ).text



def test_impedir_prestador_sem_nome(navegador):
    navegador.get(f"{URL_BASE}/prestadores/novo")

    # Preenche os campos, deixando o nome vazio
    navegador.find_element(By.NAME, "cpf").send_keys(
        f"333.{uuid.uuid4().hex[:3]}.{uuid.uuid4().hex[:3]}-66"
    )
    navegador.find_element(By.NAME, "email").send_keys(
        f"{uuid.uuid4().hex[:8]}@example.com"
    )

    navegador.find_element(
        By.CSS_SELECTOR, "button[type='submit']"
    ).click()

    # O campo nome é obrigatório no formulário
    campo_nome = navegador.find_element(By.NAME, "nome")

    assert campo_nome.get_attribute("required") is not None
    assert navegador.current_url.endswith("/prestadores/novo")


def test_listar_prestadores(navegador):
    espera = WebDriverWait(navegador, 10)

    navegador.get(f"{URL_BASE}/prestadores")

    espera.until(
        EC.text_to_be_present_in_element(
            (By.TAG_NAME, "body"),
            "Prestadores de servi"
        )
    )

    assert "Prestadores de servi" in navegador.find_element(
        By.TAG_NAME, "body"
    ).text


def test_consultar_categoria(admin_logado):
    navegador = admin_logado
    espera = WebDriverWait(navegador, 10)
    nome_categoria = f"Categoria Consulta {uuid.uuid4().hex[:6]}"

    # Cadastra a categoria pela interface
    navegador.get(f"{URL_BASE}/categorias/nova")

    navegador.find_element(By.ID, "nome").send_keys(nome_categoria)
    navegador.find_element(By.NAME, "descricao").send_keys(
        "Categoria criada para testar a consulta"
    )
    navegador.find_element(
        By.CSS_SELECTOR, "button[type='submit']"
    ).click()

    # Abre a listagem e localiza a categoria
    navegador.get(f"{URL_BASE}/categorias")
    linha = espera.until(
        EC.presence_of_element_located(
            (By.XPATH, f"//tr[td[contains(., '{nome_categoria}')]]")
        )
    )

    # Verifica se a categoria aparece na listagem
    assert nome_categoria in linha.text


def test_impedir_desativar_categoria_inativa_novamente(admin_logado):
    navegador = admin_logado
    espera = WebDriverWait(navegador, 10)
    nome_categoria = f"Categoria Inativa {uuid.uuid4().hex[:6]}"

    # Cadastra a categoria
    navegador.get(f"{URL_BASE}/categorias/nova")
    navegador.find_element(By.ID, "nome").send_keys(nome_categoria)
    navegador.find_element(By.NAME, "descricao").send_keys(
        "Teste de desativacao repetida"
    )
    navegador.find_element(
        By.CSS_SELECTOR, "button[type='submit']"
    ).click()

    # Localiza a categoria na listagem
    navegador.get(f"{URL_BASE}/categorias")
    linha = espera.until(
        EC.presence_of_element_located(
            (By.XPATH, f"//tr[td[contains(., '{nome_categoria}')]]")
        )
    )

    # Desativa a categoria pela primeira vez
    navegador.execute_script("window.confirm = () => true;")
    botao_desativar = linha.find_element(
        By.XPATH, ".//button[contains(., 'Desativar')]"
    )
    botao_desativar.click()

    # Aguarda a listagem após a primeira desativação
    espera.until(
        EC.text_to_be_present_in_element(
            (By.TAG_NAME, "body"),
            nome_categoria
        )
    )

    # Tenta desativar novamente
    navegador.get(f"{URL_BASE}/categorias")
    linha = espera.until(
        EC.presence_of_element_located(
            (By.XPATH, f"//tr[td[contains(., '{nome_categoria}')]]")
        )
    )

    # Se a categoria já estiver inativa, verifica o comportamento da interface
    assert "Ativar" in linha.text



def test_impedir_reativar_categoria_ativa_novamente(admin_logado):
    navegador = admin_logado
    espera = WebDriverWait(navegador, 10)
    nome_categoria = f"Categoria Ativa {uuid.uuid4().hex[:6]}"

    # Cadastra a categoria, que começa ativa
    navegador.get(f"{URL_BASE}/categorias/nova")
    navegador.find_element(By.ID, "nome").send_keys(nome_categoria)
    navegador.find_element(By.NAME, "descricao").send_keys(
        "Teste de ativacao repetida"
    )
    navegador.find_element(
        By.CSS_SELECTOR, "button[type='submit']"
    ).click()

    # Abre a listagem e localiza a categoria
    navegador.get(f"{URL_BASE}/categorias")
    linha = espera.until(
        EC.presence_of_element_located(
            (By.XPATH, f"//tr[td[contains(., '{nome_categoria}')]]")
        )
    )

    # Confirma que a categoria já está ativa
    assert "Desativar" in linha.text

    # Uma categoria ativa não deve apresentar a opção "Ativar"
    assert "Ativar" not in linha.text



def test_ativar_categoria_inexistente(admin_logado):
    navegador = admin_logado

    # Envia a requisição POST usando a sessão autenticada do navegador
    resultado = navegador.execute_async_script("""
        const callback = arguments[arguments.length - 1];

        fetch('/categorias/999999/ativar', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/x-www-form-urlencoded'
            },
            body: ''
        })
        .then(async resposta => ({
            status: resposta.status,
            texto: await resposta.text()
        }))
        .then(callback)
        .catch(erro => callback({
            erro: erro.toString()
        }));
    """)

    assert "erro" not in resultado
    assert resultado["status"] == 200
    assert "Categoria não encontrada." in resultado["texto"]



def test_consultar_prestador_com_servicos(admin_logado):
    navegador = admin_logado
    espera = WebDriverWait(navegador, 10)

    sufixo = uuid.uuid4().hex[:6]
    nome_categoria = f"Categoria Prestador {sufixo}"
    nome_prestador = f"Prestador Consulta {sufixo}"
    cpf = f"111.{uuid.uuid4().hex[:3]}.{uuid.uuid4().hex[:3]}-44"
    email = f"prestador-{sufixo}@example.com"

    # Cadastra uma categoria para associar ao prestador
    navegador.get(f"{URL_BASE}/categorias/nova")
    navegador.find_element(By.ID, "nome").send_keys(nome_categoria)
    navegador.find_element(By.NAME, "descricao").send_keys(
        "Categoria para teste de consulta do prestador"
    )
    navegador.find_element(
        By.CSS_SELECTOR, "button[type='submit']"
    ).click()

    # Abre o formulário de cadastro do prestador
    navegador.get(f"{URL_BASE}/prestadores/novo")

    espera.until(
    EC.presence_of_element_located((By.NAME, "nome"))
)

    navegador.find_element(By.NAME, "nome").send_keys(nome_prestador)
    navegador.find_element(By.NAME, "cpf").send_keys(cpf)
    navegador.find_element(By.NAME, "email").send_keys(email)
    navegador.find_element(By.NAME, "senha").send_keys(
        "SenhaTeste123!"
    )

    # Seleciona a categoria de serviço
    checkbox = espera.until(
        EC.presence_of_element_located((
            By.XPATH,
            f"//input[@name='categorias' and "
            f"following-sibling::text()[contains(., '{nome_categoria}')]]"
        ))
    )
    checkbox.click()

    navegador.find_element(
        By.CSS_SELECTOR, "button[type='submit']"
    ).click()

    # Abre a listagem e consulta o prestador cadastrado
    navegador.get(f"{URL_BASE}/prestadores")
    linha = espera.until(
        EC.presence_of_element_located((
            By.XPATH,
            f"//tr[td[contains(., '{nome_prestador}')]]"
        ))
    )
    linha.find_element(
        By.XPATH, ".//a[contains(., 'Consultar')]"
    ).click()

    # Confirma os dados e o serviço na página de detalhes
    espera.until(
        EC.text_to_be_present_in_element(
            (By.TAG_NAME, "body"),
            nome_categoria
        )
    )
    texto_pagina = navegador.find_element(By.TAG_NAME, "body").text

    assert nome_prestador in texto_pagina
    assert nome_categoria in texto_pagina
