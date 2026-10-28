
import pytest
from app import app as aplicacao
from database import get_db


@pytest.fixture
def cliente(tmp_path):
    banco_original = aplicacao.config["DATABASE"]
    aplicacao.config["TESTING"] = True
    aplicacao.config["DATABASE"] = str(tmp_path / "teste.db")

    with aplicacao.app_context():
        db = get_db()
        db.execute("""
            CREATE TABLE IF NOT EXISTS categorias (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nome TEXT NOT NULL UNIQUE,
                descricao TEXT,
                ativo INTEGER NOT NULL DEFAULT 1,
                data_criacao TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        db.execute("""
            CREATE TABLE IF NOT EXISTS prestadores (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nome TEXT NOT NULL,
                cpf TEXT NOT NULL UNIQUE,
                email TEXT NOT NULL UNIQUE,
                telefone TEXT,
                especialidade TEXT,
                ativo INTEGER NOT NULL DEFAULT 1,
                data_criacao TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        db.commit()

    with aplicacao.test_client() as cliente_teste:
        yield cliente_teste

    aplicacao.config["DATABASE"] = banco_original
    aplicacao.config["TESTING"] = False


def test_listar_categorias(cliente):
    resposta = cliente.get("/categorias")
    assert resposta.status_code == 200
    assert b"Categorias de servi" in resposta.data


def test_cadastrar_categoria(cliente):
    resposta = cliente.post("/categorias/nova", data={
        "nome": "Jardinagem",
        "descricao": "Manutencao de jardins"
    }, follow_redirects=True)

    assert resposta.status_code == 200
    assert "Jardinagem" in resposta.get_data(as_text=True)


def test_impedir_categoria_sem_nome(cliente):
    resposta = cliente.post("/categorias/nova", data={
        "nome": "",
        "descricao": "Categoria sem nome"
    }, follow_redirects=True)

    assert resposta.status_code == 200
    assert "obrigatório" in resposta.get_data(as_text=True)


def test_listar_prestadores(cliente):
    resposta = cliente.get("/prestadores")
    assert resposta.status_code == 200
    assert b"Prestadores de servi" in resposta.data


def test_cadastrar_prestador(cliente):
    resposta = cliente.post("/prestadores/novo", data={
        "nome": "Prestador de Teste",
        "cpf": "111.222.333-44",
        "email": "teste@example.com",
        "telefone": "31999999999",
        "especialidade": "Eletrica"
    }, follow_redirects=True)

    assert resposta.status_code == 200
    assert "Prestador de Teste" in resposta.get_data(as_text=True)


def test_impedir_prestador_sem_nome(cliente):
    resposta = cliente.post("/prestadores/novo", data={
        "nome": "",
        "cpf": "111.222.333-44",
        "email": "teste@example.com",
        "telefone": "",
        "especialidade": ""
    }, follow_redirects=True)

    assert resposta.status_code == 200
    assert "obrigatórios" in resposta.get_data(as_text=True)


def test_consultar_categoria(cliente):
    cliente.post("/categorias/nova", data={
        "nome": "Pintura",
        "descricao": "Pintura residencial"
    })

    resposta = cliente.get("/categorias")
    assert resposta.status_code == 200

    # Localiza o ID da categoria cadastrada no banco de teste
    with aplicacao.app_context():
        categoria = get_db().execute(
            "SELECT id FROM categorias WHERE nome = ?",
            ("Pintura",)
        ).fetchone()

    resposta = cliente.get(f"/categorias/{categoria['id']}")
    assert resposta.status_code == 200
    assert b"Pintura" in resposta.data


def test_editar_categoria(cliente):
    cliente.post("/categorias/nova", data={
        "nome": "Hidraulica",
        "descricao": "Servicos de agua"
    })

    with aplicacao.app_context():
        categoria = get_db().execute(
            "SELECT id FROM categorias WHERE nome = ?",
            ("Hidraulica",)
        ).fetchone()

    resposta = cliente.post(
        f"/categorias/{categoria['id']}/editar",
        data={
            "nome": "Hidraulica residencial",
            "descricao": "Reparos domesticos"
        },
        follow_redirects=True
    )

    assert resposta.status_code == 200
    assert "Hidraulica residencial" in resposta.get_data(as_text=True)


def test_desativar_categoria(cliente):
    cliente.post("/categorias/nova", data={
        "nome": "Limpeza",
        "descricao": "Limpeza geral"
    })

    with aplicacao.app_context():
        categoria = get_db().execute(
            "SELECT id FROM categorias WHERE nome = ?",
            ("Limpeza",)
        ).fetchone()

    resposta = cliente.post(
        f"/categorias/{categoria['id']}/desativar",
        follow_redirects=True
    )

    assert resposta.status_code == 200
    assert "Inativa" in resposta.get_data(as_text=True)


def test_impedir_categoria_duplicada(cliente):
    dados = {"nome": "Eletrica", "descricao": "Instalacoes"}
    cliente.post("/categorias/nova", data=dados)
    resposta = cliente.post(
        "/categorias/nova",
        data=dados,
        follow_redirects=True
    )

    assert resposta.status_code == 200
    assert "Já existe uma categoria" in resposta.get_data(as_text=True)


def test_impedir_prestador_duplicado(cliente):
    dados = {
        "nome": "Prestador Teste",
        "cpf": "111.222.333-44",
        "email": "duplicado@example.com",
        "telefone": "",
        "especialidade": "Pintura"
    }

    cliente.post("/prestadores/novo", data=dados)
    dados["nome"] = "Outro Prestador"

    resposta = cliente.post(
        "/prestadores/novo",
        data=dados,
        follow_redirects=True
    )

    assert resposta.status_code == 200
    assert "Já existe um prestador" in resposta.get_data(as_text=True)


def test_reativar_categoria(cliente):
    cliente.post("/categorias/nova", data={
        "nome": "Jardinagem para reativar",
        "descricao": "Teste de reativacao"
    })

    with aplicacao.app_context():
        categoria = get_db().execute(
            "SELECT id FROM categorias WHERE nome = ?",
            ("Jardinagem para reativar",)
        ).fetchone()

    # Primeiro, desativa a categoria.
    cliente.post(f"/categorias/{categoria['id']}/desativar")

    # Depois, reativa a categoria.
    resposta = cliente.post(
        f"/categorias/{categoria['id']}/ativar",
        follow_redirects=True
    )

    assert resposta.status_code == 200
    assert "Jardinagem para reativar" in resposta.get_data(as_text=True)
    assert "Ativa" in resposta.get_data(as_text=True)

    with aplicacao.app_context():
        categoria_atualizada = get_db().execute(
            "SELECT ativo FROM categorias WHERE id = ?",
            (categoria["id"],)
        ).fetchone()

    assert categoria_atualizada["ativo"] == 1


def test_impedir_desativar_categoria_inativa_novamente(cliente):
    cliente.post("/categorias/nova", data={
        "nome": "Categoria ja inativa",
        "descricao": "Teste de desativacao repetida"
    })

    with aplicacao.app_context():
        categoria = get_db().execute(
            "SELECT id FROM categorias WHERE nome = ?",
            ("Categoria ja inativa",)
        ).fetchone()

    cliente.post(f"/categorias/{categoria['id']}/desativar")

    resposta = cliente.post(
        f"/categorias/{categoria['id']}/desativar",
        follow_redirects=True
    )

    assert resposta.status_code == 200
    assert "Essa categoria já está desativada." in resposta.get_data(
        as_text=True
    )


def test_impedir_reativar_categoria_ativa_novamente(cliente):
    cliente.post("/categorias/nova", data={
        "nome": "Categoria ja ativa",
        "descricao": "Teste de ativacao repetida"
    })

    with aplicacao.app_context():
        categoria = get_db().execute(
            "SELECT id FROM categorias WHERE nome = ?",
            ("Categoria ja ativa",)
        ).fetchone()

    resposta = cliente.post(
        f"/categorias/{categoria['id']}/ativar",
        follow_redirects=True
    )

    assert resposta.status_code == 200
    assert "Essa categoria já está ativa." in resposta.get_data(
        as_text=True
    )


def test_ativar_categoria_inexistente(cliente):
    resposta = cliente.post(
        "/categorias/999999/ativar",
        follow_redirects=True
    )

    assert resposta.status_code == 200
    assert "Categoria não encontrada." in resposta.get_data(as_text=True)