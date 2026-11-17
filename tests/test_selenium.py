import uuid

import pytest
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import Select, WebDriverWait

from tests.conftest import (
    EMAIL_ADMIN,
    EMAIL_CLIENTE,
    EMAIL_PRESTADOR,
    SENHA_ADMIN,
    SENHA_CLIENTE,
    SENHA_PRESTADOR,
)

TIMEOUT = 10


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def esperar(navegador):
    return WebDriverWait(navegador, TIMEOUT)


def entrar(navegador, url_base, email, senha):
    espera = esperar(navegador)
    navegador.get(f"{url_base}/login")
    espera.until(EC.visibility_of_element_located((By.NAME, "email"))).send_keys(email)
    navegador.find_element(By.NAME, "senha").send_keys(senha)
    navegador.find_element(By.CSS_SELECTOR, "main form button[type='submit']").click()
    espera.until(EC.url_contains("/painel"))
    assert "Login realizado com sucesso" in navegador.page_source


def sair(navegador, url_base):
    # logout via GET redireciona para /login
    navegador.get(f"{url_base}/logout")


def _primeira_categoria_valor(navegador):
    opcoes = navegador.find_elements(
        By.CSS_SELECTOR, "select[name='categoria_id'] option"
    )
    for opcao in opcoes:
        valor = opcao.get_attribute("value")
        if valor:
            return valor
    pytest.skip("Nenhuma categoria disponível para o teste")


def criar_pedido(navegador, url_base, descricao):
    espera = esperar(navegador)
    navegador.get(f"{url_base}/pedidos/novo")
    espera.until(EC.presence_of_element_located((By.NAME, "categoria_id")))
    valor = _primeira_categoria_valor(navegador)
    Select(navegador.find_element(By.NAME, "categoria_id")).select_by_value(valor)
    navegador.find_element(By.NAME, "descricao").send_keys(descricao)
    navegador.find_element(By.CSS_SELECTOR, "main form button[type='submit']").click()
    espera.until(
        EC.text_to_be_present_in_element((By.TAG_NAME, "body"), "Pedido enviado")
    )


# ---------------------------------------------------------------------------
# Login / proteção de rota
# ---------------------------------------------------------------------------

def test_login_invalido(navegador, url_base):
    espera = esperar(navegador)
    navegador.get(f"{url_base}/login")
    navegador.find_element(By.NAME, "email").send_keys("naoexiste@example.com")
    navegador.find_element(By.NAME, "senha").send_keys("errada123")
    navegador.find_element(By.CSS_SELECTOR, "main form button[type='submit']").click()
    espera.until(
        EC.text_to_be_present_in_element(
            (By.TAG_NAME, "body"), "E-mail ou senha inválidos"
        )
    )


def test_proteger_cadastro_de_categoria(navegador, url_base):
    espera = esperar(navegador)
    navegador.get(f"{url_base}/categorias/nova")
    espera.until(EC.url_contains("/login"))
    assert "Entrar no ChamaAí" in navegador.page_source


def test_cliente_nao_acessa_admin(navegador, url_base):
    entrar(navegador, url_base, EMAIL_CLIENTE, SENHA_CLIENTE)
    navegador.get(f"{url_base}/clientes")
    espera = esperar(navegador)
    espera.until(EC.presence_of_element_located((By.TAG_NAME, "body")))
    assert "Acesso restrito ao administrador" in navegador.page_source


def test_login_prestador_abre_painel(navegador, url_base):
    entrar(navegador, url_base, EMAIL_PRESTADOR, SENHA_PRESTADOR)
    assert "Painel prestador" in navegador.page_source


# ---------------------------------------------------------------------------
# Categorias (admin)
# ---------------------------------------------------------------------------

def test_cadastrar_categoria_no_navegador(navegador, url_base):
    entrar(navegador, url_base, EMAIL_ADMIN, SENHA_ADMIN)
    espera = esperar(navegador)
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
    espera = esperar(navegador)
    navegador.get(f"{url_base}/categorias/nova")
    navegador.find_element(By.NAME, "descricao").send_keys(
        "Categoria sem nome para teste"
    )
    navegador.find_element(By.CSS_SELECTOR, "main form button[type='submit']").click()
    espera.until(EC.visibility_of_element_located((By.ID, "nome")))
    assert navegador.current_url.endswith("/categorias/nova")


def test_editar_categoria(navegador, url_base):
    entrar(navegador, url_base, EMAIL_ADMIN, SENHA_ADMIN)
    espera = esperar(navegador)
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
                f"//*[contains(text(), '{nome_original}')]"
                "/ancestor::*[self::tr or self::div][1]//a[contains(@href, '/editar')]",
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


def test_desativar_e_reativar_categoria(navegador, url_base):
    entrar(navegador, url_base, EMAIL_ADMIN, SENHA_ADMIN)
    espera = esperar(navegador)
    nome_categoria = f"Categoria Status {uuid.uuid4().hex[:6]}"
    navegador.get(f"{url_base}/categorias/nova")
    navegador.find_element(By.ID, "nome").send_keys(nome_categoria)
    navegador.find_element(By.NAME, "descricao").send_keys("Teste de status")
    navegador.find_element(By.CSS_SELECTOR, "main form button[type='submit']").click()
    espera.until(EC.text_to_be_present_in_element((By.TAG_NAME, "body"), nome_categoria))

    navegador.get(f"{url_base}/categorias")
    navegador.execute_script("window.confirm = () => true;")
    linha = espera.until(
        EC.presence_of_element_located(
            (By.XPATH, f"//tr[td[contains(., '{nome_categoria}')]]")
        )
    )
    linha.find_element(By.XPATH, ".//button[normalize-space()='Desativar']").click()
    espera.until(
        EC.text_to_be_present_in_element(
            (By.XPATH, f"//tr[td[contains(., '{nome_categoria}')]]"), "Inativa"
        )
    )

    navegador.execute_script("window.confirm = () => true;")
    linha = navegador.find_element(
        By.XPATH, f"//tr[td[contains(., '{nome_categoria}')]]"
    )
    linha.find_element(By.XPATH, ".//button[normalize-space()='Ativar']").click()
    espera.until(
        EC.text_to_be_present_in_element(
            (By.XPATH, f"//tr[td[contains(., '{nome_categoria}')]]"), "Ativa"
        )
    )


def test_impedir_categoria_duplicada(navegador, url_base):
    entrar(navegador, url_base, EMAIL_ADMIN, SENHA_ADMIN)
    espera = esperar(navegador)
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
        EC.text_to_be_present_in_element(
            (By.TAG_NAME, "body"), "Já existe uma categoria"
        )
    )


# ---------------------------------------------------------------------------
# Prestadores
# ---------------------------------------------------------------------------

def test_cadastrar_prestador(navegador, url_base):
    espera = esperar(navegador)
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


# ---------------------------------------------------------------------------
# Clientes
# ---------------------------------------------------------------------------

def test_cadastrar_cliente(navegador, url_base):
    espera = esperar(navegador)
    email = f"cliente-{uuid.uuid4().hex[:8]}@example.com"
    navegador.get(f"{url_base}/clientes/novo")
    navegador.find_element(By.NAME, "nome").send_keys("Cliente Teste")
    navegador.find_element(By.NAME, "email").send_keys(email)
    navegador.find_element(By.NAME, "senha").send_keys("SenhaTeste123!")
    navegador.find_element(By.CSS_SELECTOR, "main form button[type='submit']").click()
    espera.until(EC.url_contains("/login"))
    assert "Cadastro realizado com sucesso" in navegador.page_source


def test_impedir_cliente_sem_nome(navegador, url_base):
    email = f"cliente-{uuid.uuid4().hex[:8]}@example.com"
    navegador.get(f"{url_base}/clientes/novo")
    navegador.find_element(By.NAME, "email").send_keys(email)
    navegador.find_element(By.NAME, "senha").send_keys("SenhaTeste123!")
    campo_nome = navegador.find_element(By.NAME, "nome")
    assert campo_nome.get_attribute("required") is not None


# ---------------------------------------------------------------------------
# Fluxo de pedido: criar -> aceitar -> finalizar -> avaliar -> notificar
# ---------------------------------------------------------------------------

DESCRICAO_PEDIDO_AVALIACAO = "Pedido para fluxo Selenium de avaliacao"


def test_fluxo_cliente_cria_pedido(navegador, url_base):
    entrar(navegador, url_base, EMAIL_CLIENTE, SENHA_CLIENTE)
    criar_pedido(navegador, url_base, DESCRICAO_PEDIDO_AVALIACAO)
    assert DESCRICAO_PEDIDO_AVALIACAO in navegador.page_source


def test_fluxo_prestador_aceita_e_finaliza(navegador, url_base):
    entrar(navegador, url_base, EMAIL_PRESTADOR, SENHA_PRESTADOR)
    espera = esperar(navegador)
    navegador.get(f"{url_base}/pedidos")

    # localiza a linha do pedido de avaliação e clica em "Aceitar"
    linha = espera.until(
        EC.presence_of_element_located(
            (
                By.XPATH,
                f"//tr[td[contains(., '{DESCRICAO_PEDIDO_AVALIACAO}')]]",
            )
        )
    )
    linha.find_element(By.XPATH, ".//form[contains(@action, '/aceitar')]//button").click()
    espera.until(
        EC.text_to_be_present_in_element((By.TAG_NAME, "body"), "Pedido aceito")
    )

    # após o aceite, o status vira 'aceito' e aparece o botão Finalizar
    navegador.get(f"{url_base}/pedidos")
    linha = espera.until(
        EC.presence_of_element_located(
            (
                By.XPATH,
                f"//tr[td[contains(., '{DESCRICAO_PEDIDO_AVALIACAO}')]]",
            )
        )
    )
    linha.find_element(
        By.XPATH, ".//form[contains(@action, '/finalizar')]//button"
    ).click()
    espera.until(
        EC.text_to_be_present_in_element((By.TAG_NAME, "body"), "Pedido finalizado")
    )


def test_fluxo_cliente_avalia_pedido(navegador, url_base):
    entrar(navegador, url_base, EMAIL_CLIENTE, SENHA_CLIENTE)
    espera = esperar(navegador)
    navegador.get(f"{url_base}/pedidos")

    linha = espera.until(
        EC.presence_of_element_located(
            (
                By.XPATH,
                f"//tr[td[contains(., '{DESCRICAO_PEDIDO_AVALIACAO}')]]",
            )
        )
    )
    # o botão "Avaliar" pode ser form GET ou link
    botoes = linha.find_elements(
        By.XPATH,
        ".//form[contains(@action, '/avaliar')]//button"
        " | .//a[contains(@href, '/avaliar')]",
    )
    assert botoes, "Botão de avaliar não encontrado no pedido finalizado"
    botoes[0].click()

    espera.until(EC.presence_of_element_located((By.NAME, "nota")))
    navegador.find_element(
        By.CSS_SELECTOR, "input[name='nota'][value='excelente']"
    ).click()
    navegador.find_element(By.NAME, "comentario").send_keys(
        "Atendimento excelente, teste Selenium."
    )
    navegador.find_element(By.CSS_SELECTOR, "main form button[type='submit']").click()
    espera.until(
        EC.text_to_be_present_in_element(
            (By.TAG_NAME, "body"), "Avaliação enviada"
        )
    )


def test_fluxo_prestador_ve_avaliacoes(navegador, url_base):
    entrar(navegador, url_base, EMAIL_PRESTADOR, SENHA_PRESTADOR)
    espera = esperar(navegador)
    navegador.get(f"{url_base}/minhas-avaliacoes")
    espera.until(
        EC.text_to_be_present_in_element((By.TAG_NAME, "body"), "Minhas avaliações")
    )
    espera.until(
        EC.text_to_be_present_in_element(
            (By.TAG_NAME, "body"), "Atendimento excelente, teste Selenium."
        )
    )


def test_fluxo_prestador_recebe_notificacao(navegador, url_base):
    entrar(navegador, url_base, EMAIL_PRESTADOR, SENHA_PRESTADOR)
    espera = esperar(navegador)
    navegador.get(f"{url_base}/notificacoes")
    espera.until(
        EC.text_to_be_present_in_element((By.TAG_NAME, "body"), "Notificações")
    )
    corpo = navegador.find_element(By.TAG_NAME, "body").text.lower()
    assert "avalia" in corpo or "pedido" in corpo


# ---------------------------------------------------------------------------
# Cancelamento de pedido aberto (cliente)
# ---------------------------------------------------------------------------

def test_cliente_cancela_pedido_aberto(navegador, url_base):
    entrar(navegador, url_base, EMAIL_CLIENTE, SENHA_CLIENTE)
    descricao = f"Pedido para cancelar {uuid.uuid4().hex[:6]}"
    criar_pedido(navegador, url_base, descricao)

    espera = esperar(navegador)
    navegador.get(f"{url_base}/pedidos")
    navegador.execute_script("window.confirm = () => true;")
    linha = espera.until(
        EC.presence_of_element_located(
            (By.XPATH, f"//tr[td[contains(., '{descricao}')]]")
        )
    )
    linha.find_element(
        By.XPATH, ".//form[contains(@action, '/cancelar')]//button"
    ).click()
    espera.until(
        EC.text_to_be_present_in_element((By.TAG_NAME, "body"), "Pedido cancelado")
    )


# ---------------------------------------------------------------------------
# Relatório (admin)
# ---------------------------------------------------------------------------

def test_admin_acessa_relatorio_pedidos(navegador, url_base):
    entrar(navegador, url_base, EMAIL_ADMIN, SENHA_ADMIN)
    espera = esperar(navegador)
    navegador.get(f"{url_base}/relatorios/pedidos")
    espera.until(
        EC.text_to_be_present_in_element(
            (By.TAG_NAME, "body"), "Relatório de Pedidos"
        )
    )
    assert "Totais por status" in navegador.page_source

    # filtra por finalizado e confirma que a página recarrega com o filtro
    Select(navegador.find_element(By.NAME, "status")).select_by_value("finalizado")
    navegador.find_element(By.CSS_SELECTOR, "main form button[type='submit']").click()
    espera.until(
        EC.text_to_be_present_in_element(
            (By.TAG_NAME, "body"), "Relatório de Pedidos"
        )
    )


def test_cliente_nao_acessa_relatorio(navegador, url_base):
    entrar(navegador, url_base, EMAIL_CLIENTE, SENHA_CLIENTE)
    navegador.get(f"{url_base}/relatorios/pedidos")
    espera = esperar(navegador)
    espera.until(EC.presence_of_element_located((By.TAG_NAME, "body")))
    assert "Acesso restrito ao administrador" in navegador.page_source