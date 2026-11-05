from tests.conftest import EMAIL_ADMIN, EMAIL_CLIENTE, EMAIL_PRESTADOR, SENHA_ADMIN, SENHA_CLIENTE, SENHA_PRESTADOR


def login(cliente_http, email, senha):
    return cliente_http.post(
        "/login",
        data={"email": email, "senha": senha},
        follow_redirects=True,
    )


def test_login_admin_direciona_painel(cliente_http):
    resposta = login(cliente_http, EMAIL_ADMIN, SENHA_ADMIN)
    assert resposta.status_code == 200
    assert "Painel admin".encode() in resposta.data or b"Painel" in resposta.data
    assert "Login realizado com sucesso".encode() in resposta.data


def test_login_invalido(cliente_http):
    resposta = login(cliente_http, "naoexiste@example.com", "errada123")
    assert "E-mail ou senha inválidos".encode() in resposta.data


def test_cliente_nao_acessa_cadastro_categoria(cliente_http):
    login(cliente_http, EMAIL_CLIENTE, SENHA_CLIENTE)
    resposta = cliente_http.get("/categorias/nova", follow_redirects=True)
    assert "Acesso restrito ao administrador".encode() in resposta.data


def test_visitante_nao_acessa_clientes(cliente_http):
    resposta = cliente_http.get("/clientes", follow_redirects=True)
    assert b"login" in resposta.data.lower() or "Entrar no ChamaA".encode() in resposta.data


def test_crud_categoria_completo(cliente_http):
    login(cliente_http, EMAIL_ADMIN, SENHA_ADMIN)
    nome = "Categoria Flask 01"
    criar = cliente_http.post(
        "/categorias/nova",
        data={"nome": nome, "descricao": "Teste"},
        follow_redirects=True,
    )
    assert "Categoria cadastrada com sucesso".encode() in criar.data
    assert nome.encode() in criar.data

    listagem = cliente_http.get("/categorias")
    assert nome.encode() in listagem.data


def test_crud_cliente_admin(cliente_http):
    login(cliente_http, EMAIL_ADMIN, SENHA_ADMIN)
    email = "novo.cliente.crud@example.com"
    criar = cliente_http.post(
        "/clientes/novo",
        data={
            "nome": "Cliente CRUD",
            "email": email,
            "senha": "SenhaTeste123!",
            "telefone": "31911112222",
            "cidade": "Contagem",
        },
        follow_redirects=True,
    )
    assert "Cadastro realizado com sucesso".encode() in criar.data
    listagem = cliente_http.get("/clientes")
    assert b"Cliente CRUD" in listagem.data


def test_crud_servico_prestador(cliente_http):
    login(cliente_http, EMAIL_PRESTADOR, SENHA_PRESTADOR)
    categorias = cliente_http.get("/servicos/novo")
    assert categorias.status_code == 200
    from app import app
    from database import get_db

    with app.app_context():
        db = get_db()
        categoria = db.execute(
            "SELECT id FROM categorias WHERE ativo = 1 LIMIT 1"
        ).fetchone()
        prestador = db.execute(
            "SELECT id FROM prestadores WHERE email = ?",
            (EMAIL_PRESTADOR,),
        ).fetchone()
        categoria_id = categoria["id"]
        prestador_id = prestador["id"]

    criar = cliente_http.post(
        "/servicos/novo",
        data={
            "titulo": "Instalação de tomada",
            "descricao": "Serviço de teste",
            "categoria_id": str(categoria_id),
            "prestador_id": str(prestador_id),
            "preco": "80",
        },
        follow_redirects=True,
    )
    assert "Serviço cadastrado com sucesso".encode() in criar.data
    assert "Instalação de tomada".encode() in criar.data


def test_prestador_nao_acessa_lista_clientes(cliente_http):
    login(cliente_http, EMAIL_PRESTADOR, SENHA_PRESTADOR)
    resposta = cliente_http.get("/clientes", follow_redirects=True)
    assert "Acesso restrito ao administrador".encode() in resposta.data
