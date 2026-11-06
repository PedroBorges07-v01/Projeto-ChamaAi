import os
import socket
import tempfile
import threading
import time

import pytest
from selenium import webdriver
from werkzeug.security import generate_password_hash
from werkzeug.serving import make_server

from app import app
from database import get_db, init_db


EMAIL_ADMIN = "admin-teste@example.com"
SENHA_ADMIN = "SenhaTeste123!"
EMAIL_CLIENTE = "cliente-teste@example.com"
SENHA_CLIENTE = "SenhaTeste123!"
EMAIL_PRESTADOR = "prestador-teste@example.com"
SENHA_PRESTADOR = "SenhaTeste123!"

# Pausa, em segundos, entre um teste e o próximo.
# Para mudar sem editar o arquivo:  INTERVALO_ENTRE_TESTES=5 pytest
INTERVALO_ENTRE_TESTES = float(os.environ.get("INTERVALO_ENTRE_TESTES", "2"))

# Para ver o Chrome na tela:  NAVEGADOR_VISIVEL=1 pytest
NAVEGADOR_VISIVEL = os.environ.get("NAVEGADOR_VISIVEL", "") not in ("", "0")


def _seed(db):
    if db.execute(
        "SELECT id FROM usuarios WHERE email = ?",
        (EMAIL_ADMIN,),
    ).fetchone() is None:
        db.execute(
            """
            INSERT INTO usuarios (nome, email, senha_hash, tipo)
            VALUES (?, ?, ?, 'admin')
            """,
            ("Admin Teste", EMAIL_ADMIN, generate_password_hash(SENHA_ADMIN)),
        )

    if db.execute(
        "SELECT id FROM usuarios WHERE email = ?",
        (EMAIL_CLIENTE,),
    ).fetchone() is None:
        cursor = db.execute(
            """
            INSERT INTO usuarios (nome, email, senha_hash, tipo)
            VALUES (?, ?, ?, 'cliente')
            """,
            ("Cliente Teste", EMAIL_CLIENTE, generate_password_hash(SENHA_CLIENTE)),
        )
        db.execute(
            "INSERT INTO clientes (usuario_id, telefone, cidade) VALUES (?, ?, ?)",
            (cursor.lastrowid, "31999990000", "Belo Horizonte"),
        )

    if db.execute(
        "SELECT id FROM usuarios WHERE email = ?",
        (EMAIL_PRESTADOR,),
    ).fetchone() is None:
        cursor_u = db.execute(
            """
            INSERT INTO usuarios (nome, email, senha_hash, tipo)
            VALUES (?, ?, ?, 'prestador')
            """,
            (
                "Prestador Teste",
                EMAIL_PRESTADOR,
                generate_password_hash(SENHA_PRESTADOR),
            ),
        )
        db.execute(
            """
            INSERT INTO prestadores
            (nome, cpf, email, telefone, especialidade, usuario_id)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                "Prestador Teste",
                "000.000.000-00",
                EMAIL_PRESTADOR,
                "31988887777",
                "Elétrica",
                cursor_u.lastrowid,
            ),
        )

    if db.execute("SELECT id FROM categorias WHERE nome = ?", ("Elétrica",)).fetchone() is None:
        db.execute(
            "INSERT INTO categorias (nome, descricao) VALUES (?, ?)",
            ("Elétrica", "Serviços elétricos"),
        )

    db.commit()


@pytest.fixture(scope="session")
def arquivo_banco():
    handle, caminho = tempfile.mkstemp(suffix=".db")
    os.close(handle)
    yield caminho
    try:
        os.unlink(caminho)
    except OSError:
        pass


@pytest.fixture(scope="session")
def app_teste(arquivo_banco):
    app.config["TESTING"] = True
    app.config["DATABASE"] = arquivo_banco
    app.config["SECRET_KEY"] = "chave-teste"
    with app.app_context():
        init_db()
        _seed(get_db())
    return app


@pytest.fixture
def cliente_http(app_teste):
    return app_teste.test_client()


@pytest.fixture(scope="session")
def url_base(app_teste):
    sock = socket.socket()
    sock.bind(("127.0.0.1", 0))
    porta = sock.getsockname()[1]
    sock.close()

    servidor = make_server("127.0.0.1", porta, app_teste)
    thread = threading.Thread(target=servidor.serve_forever, daemon=True)
    thread.start()
    time.sleep(0.3)
    yield f"http://127.0.0.1:{porta}"
    servidor.shutdown()


@pytest.fixture(scope="session")
def _navegador():
    # Uma única janela do Chrome para a sessão inteira de testes:
    # abre aqui e só fecha (driver.quit) depois do último teste.
    opcoes = webdriver.ChromeOptions()
    if not NAVEGADOR_VISIVEL:
        opcoes.add_argument("--headless=new")
    opcoes.add_argument("--disable-gpu")
    opcoes.add_argument("--window-size=1280,900")
    opcoes.add_argument("--no-sandbox")
    driver = webdriver.Chrome(options=opcoes)
    driver.implicitly_wait(0)
    yield driver
    driver.quit()


@pytest.fixture
def navegador(request, _navegador):
    # Reaproveita o mesmo navegador, mas começa cada teste deslogado.
    _navegador.delete_all_cookies()
    try:
        _navegador.switch_to.alert.accept()
    except Exception:
        pass
    yield _navegador

    # Pausa entre os testes (não espera depois do último).
    if request.session.items[-1] is not request.node:
        time.sleep(INTERVALO_ENTRE_TESTES)