
import uuid

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC


def test_cadastrar_categoria_no_navegador():
    opcoes = webdriver.ChromeOptions()
    navegador = webdriver.Chrome(options=opcoes)
    espera = WebDriverWait(navegador, 10)

    nome_categoria = f"Teste Selenium {uuid.uuid4().hex[:6]}"

    try:
        navegador.get("http://127.0.0.1:5000/categorias/nova")

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

        espera.until(EC.url_contains("/categorias"))

        espera.until(
            EC.presence_of_element_located(
                (By.XPATH, f"//*[contains(text(), '{nome_categoria}')]")
            )
        )

        assert nome_categoria in navegador.page_source

    finally:
        navegador.quit()
