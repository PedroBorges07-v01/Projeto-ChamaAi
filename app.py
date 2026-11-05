from functools import wraps
import sqlite3

import click
from flask import Flask, flash, redirect, render_template, request, url_for
from flask_login import (
    LoginManager,
    UserMixin,
    current_user,
    login_required,
    login_user,
    logout_user,
)
from werkzeug.security import check_password_hash, generate_password_hash

from database import get_db, init_app


app = Flask(__name__)
app.config["SECRET_KEY"] = "chave-desenvolvimento-local"
app.config["TESTING"] = False

login_manager = LoginManager()
login_manager.login_view = "login"
login_manager.login_message = "Faça login para acessar esta página."
login_manager.login_message_category = "erro"
login_manager.init_app(app)

init_app(app)


class Usuario(UserMixin):
    def __init__(self, id, nome, email, senha_hash, tipo, ativo):
        self.id = str(id)
        self.nome = nome
        self.email = email
        self.senha_hash = senha_hash
        self.tipo = tipo
        self.ativo = ativo == 1


@login_manager.user_loader
def carregar_usuario(user_id):
    db = get_db()
    usuario = db.execute(
        """
        SELECT id, nome, email, senha_hash, tipo, ativo
        FROM usuarios
        WHERE id = ?
        """,
        (user_id,),
    ).fetchone()

    if usuario is None or usuario["ativo"] != 1:
        return None

    return Usuario(
        usuario["id"],
        usuario["nome"],
        usuario["email"],
        usuario["senha_hash"],
        usuario["tipo"],
        usuario["ativo"],
    )


def admin_required(view):
    @wraps(view)
    @login_required
    def wrapped_view(*args, **kwargs):
        if current_user.tipo != "admin":
            flash("Acesso restrito ao administrador.", "erro")
            return redirect(url_for("inicio"))
        return view(*args, **kwargs)

    return wrapped_view


def perfil_required(*tipos):
    def decorator(view):
        @wraps(view)
        @login_required
        def wrapped_view(*args, **kwargs):
            if current_user.tipo not in tipos:
                flash("Acesso não autorizado para este perfil.", "erro")
                return redirect(url_for("painel"))
            return view(*args, **kwargs)

        return wrapped_view

    return decorator


def destino_pos_login(usuario=None):
    tipo = usuario.tipo if usuario is not None else current_user.tipo
    if tipo == "admin":
        return url_for("painel")
    if tipo == "prestador":
        return url_for("painel")
    return url_for("painel")


def obter_prestador_atual(db=None):
    if not current_user.is_authenticated or current_user.tipo != "prestador":
        return None

    db = db or get_db()
    return db.execute(
        """
        SELECT *
        FROM prestadores
        WHERE usuario_id = ?
           OR (usuario_id IS NULL AND email = ?)
        """,
        (current_user.id, current_user.email),
    ).fetchone()


def pode_gerenciar_prestador(prestador):
    if not current_user.is_authenticated:
        return False
    if current_user.tipo == "admin":
        return True
    if current_user.tipo != "prestador" or prestador is None:
        return False
    if prestador["usuario_id"] is not None:
        return str(prestador["usuario_id"]) == current_user.id
    return prestador["email"] == current_user.email


def pode_gerenciar_servico(servico):
    if not current_user.is_authenticated:
        return False
    if current_user.tipo == "admin":
        return True
    prestador = obter_prestador_atual()
    return (
        prestador is not None
        and servico is not None
        and servico["prestador_id"] == prestador["id"]
    )


def sincronizar_usuario_prestador(db, prestador, nome, email, ativo=None):
    usuario = None
    if prestador["usuario_id"]:
        usuario = db.execute(
            "SELECT id FROM usuarios WHERE id = ?",
            (prestador["usuario_id"],),
        ).fetchone()
    if usuario is None:
        usuario = db.execute(
            """
            SELECT id FROM usuarios
            WHERE email = ? AND tipo = 'prestador'
            """,
            (prestador["email"],),
        ).fetchone()
    if usuario is None:
        return

    if ativo is None:
        db.execute(
            "UPDATE usuarios SET nome = ?, email = ? WHERE id = ?",
            (nome, email, usuario["id"]),
        )
    else:
        db.execute(
            """
            UPDATE usuarios
            SET nome = ?, email = ?, ativo = ?
            WHERE id = ?
            """,
            (nome, email, ativo, usuario["id"]),
        )


def categorias_ativas(db):
    return db.execute(
        """
        SELECT id, nome, ativo
        FROM categorias
        WHERE ativo = 1
        ORDER BY nome
        """
    ).fetchall()


def registrar_areas_prestador(db, prestador_id, ids_categorias):
    db.execute(
        "DELETE FROM prestador_servicos WHERE prestador_id = ?",
        (prestador_id,),
    )
    for categoria_id in set(ids_categorias):
        db.execute(
            """
            INSERT INTO prestador_servicos (prestador_id, categoria_id)
            VALUES (?, ?)
            """,
            (prestador_id, categoria_id),
        )


@app.cli.command("criar-admin")
def criar_admin():
    """Cria uma conta de administrador pelo terminal."""
    nome = click.prompt("Nome do administrador").strip()
    email = click.prompt("E-mail").strip().lower()

    if not nome or not email:
        click.echo("Nome e e-mail são obrigatórios.")
        return

    db = get_db()
    existente = db.execute(
        "SELECT id FROM usuarios WHERE email = ?",
        (email,),
    ).fetchone()
    if existente:
        click.echo("Já existe uma conta com esse e-mail.")
        return

    senha = click.prompt("Senha", hide_input=True, confirmation_prompt=True)
    if len(senha) < 8:
        click.echo("A senha deve ter pelo menos 8 caracteres.")
        return

    db.execute(
        """
        INSERT INTO usuarios (nome, email, senha_hash, tipo)
        VALUES (?, ?, ?, 'admin')
        """,
        (nome, email, generate_password_hash(senha)),
    )
    db.commit()
    click.echo("Administrador criado com sucesso.")


@app.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(destino_pos_login())

    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        senha = request.form.get("senha", "")
        db = get_db()
        usuario = db.execute(
            """
            SELECT id, nome, email, senha_hash, tipo, ativo
            FROM usuarios
            WHERE email = ?
            """,
            (email,),
        ).fetchone()

        if (
            usuario is not None
            and usuario["ativo"] == 1
            and check_password_hash(usuario["senha_hash"], senha)
        ):
            usuario_logado = Usuario(
                usuario["id"],
                usuario["nome"],
                usuario["email"],
                usuario["senha_hash"],
                usuario["tipo"],
                usuario["ativo"],
            )
            login_user(usuario_logado)
            flash("Login realizado com sucesso.", "sucesso")
            proximo = request.args.get("next")
            if proximo and proximo.startswith("/"):
                return redirect(proximo)
            return redirect(destino_pos_login(usuario_logado))

        flash("E-mail ou senha inválidos.", "erro")

    return render_template("login.html")


@app.route("/logout", methods=["GET", "POST"])
@login_required
def logout():
    logout_user()
    flash("Você saiu da sua conta.", "sucesso")
    return redirect(url_for("login"))


@app.route("/")
def inicio():
    db = get_db()
    totais = {
        "categorias": db.execute(
            "SELECT COUNT(*) AS total FROM categorias WHERE ativo = 1"
        ).fetchone()["total"],
        "prestadores": db.execute(
            "SELECT COUNT(*) AS total FROM prestadores WHERE ativo = 1"
        ).fetchone()["total"],
        "servicos": db.execute(
            "SELECT COUNT(*) AS total FROM servicos WHERE ativo = 1"
        ).fetchone()["total"],
    }
    return render_template("inicio.html", totais=totais)


@app.route("/painel")
@login_required
def painel():
    db = get_db()

    if current_user.tipo == "admin":
        resumo = {
            "clientes": db.execute(
                "SELECT COUNT(*) AS total FROM usuarios WHERE tipo = 'cliente'"
            ).fetchone()["total"],
            "prestadores": db.execute(
                "SELECT COUNT(*) AS total FROM prestadores"
            ).fetchone()["total"],
            "servicos": db.execute(
                "SELECT COUNT(*) AS total FROM servicos"
            ).fetchone()["total"],
            "categorias": db.execute(
                "SELECT COUNT(*) AS total FROM categorias"
            ).fetchone()["total"],
            "solicitacoes": db.execute(
                "SELECT COUNT(*) AS total FROM solicitacoes"
            ).fetchone()["total"],
        }
        return render_template("painel.html", resumo=resumo)

    if current_user.tipo == "prestador":
        prestador = obter_prestador_atual(db)
        servicos = []
        solicitacoes = []
        if prestador:
            servicos = db.execute(
                """
                SELECT s.*, c.nome AS categoria_nome
                FROM servicos s
                JOIN categorias c ON c.id = s.categoria_id
                WHERE s.prestador_id = ?
                ORDER BY s.titulo
                """,
                (prestador["id"],),
            ).fetchall()
            solicitacoes = db.execute(
                """
                SELECT sol.*, s.titulo AS servico_titulo, u.nome AS cliente_nome
                FROM solicitacoes sol
                JOIN servicos s ON s.id = sol.servico_id
                JOIN usuarios u ON u.id = sol.cliente_usuario_id
                WHERE sol.prestador_id = ?
                ORDER BY sol.data_criacao DESC
                """,
                (prestador["id"],),
            ).fetchall()
        return render_template(
            "painel.html",
            prestador=prestador,
            servicos=servicos,
            solicitacoes=solicitacoes,
        )

    solicitacoes = db.execute(
        """
        SELECT sol.*, s.titulo AS servico_titulo, p.nome AS prestador_nome
        FROM solicitacoes sol
        JOIN servicos s ON s.id = sol.servico_id
        JOIN prestadores p ON p.id = sol.prestador_id
        WHERE sol.cliente_usuario_id = ?
        ORDER BY sol.data_criacao DESC
        """,
        (current_user.id,),
    ).fetchall()
    servicos = db.execute(
        """
        SELECT s.*, p.nome AS prestador_nome, c.nome AS categoria_nome
        FROM servicos s
        JOIN prestadores p ON p.id = s.prestador_id
        JOIN categorias c ON c.id = s.categoria_id
        WHERE s.ativo = 1 AND p.ativo = 1
        ORDER BY s.titulo
        LIMIT 8
        """
    ).fetchall()
    return render_template(
        "painel.html",
        solicitacoes=solicitacoes,
        servicos=servicos,
    )


@app.route("/perfil", methods=["GET", "POST"])
@login_required
def perfil():
    db = get_db()
    cliente = None
    prestador = obter_prestador_atual(db)

    if current_user.tipo == "cliente":
        cliente = db.execute(
            "SELECT * FROM clientes WHERE usuario_id = ?",
            (current_user.id,),
        ).fetchone()

    if request.method == "POST":
        nome = request.form.get("nome", "").strip()
        email = request.form.get("email", "").strip().lower()
        senha = request.form.get("senha", "")
        telefone = request.form.get("telefone", "").strip()
        cidade = request.form.get("cidade", "").strip()
        especialidade = request.form.get("especialidade", "").strip()

        if not nome or not email:
            flash("Nome e e-mail são obrigatórios.", "erro")
        elif senha and len(senha) < 8:
            flash("A senha deve ter pelo menos 8 caracteres.", "erro")
        else:
            existente = db.execute(
                "SELECT id FROM usuarios WHERE email = ? AND id != ?",
                (email, current_user.id),
            ).fetchone()
            if existente:
                flash("Este e-mail já está cadastrado.", "erro")
            else:
                try:
                    if senha:
                        db.execute(
                            """
                            UPDATE usuarios
                            SET nome = ?, email = ?, senha_hash = ?
                            WHERE id = ?
                            """,
                            (
                                nome,
                                email,
                                generate_password_hash(senha),
                                current_user.id,
                            ),
                        )
                    else:
                        db.execute(
                            """
                            UPDATE usuarios
                            SET nome = ?, email = ?
                            WHERE id = ?
                            """,
                            (nome, email, current_user.id),
                        )

                    if current_user.tipo == "cliente":
                        if cliente:
                            db.execute(
                                """
                                UPDATE clientes
                                SET telefone = ?, cidade = ?
                                WHERE usuario_id = ?
                                """,
                                (telefone, cidade, current_user.id),
                            )
                        else:
                            db.execute(
                                """
                                INSERT INTO clientes (usuario_id, telefone, cidade)
                                VALUES (?, ?, ?)
                                """,
                                (current_user.id, telefone, cidade),
                            )

                    if current_user.tipo == "prestador" and prestador:
                        db.execute(
                            """
                            UPDATE prestadores
                            SET nome = ?, email = ?, telefone = ?, especialidade = ?
                            WHERE id = ?
                            """,
                            (
                                nome,
                                email,
                                telefone,
                                especialidade,
                                prestador["id"],
                            ),
                        )

                    db.commit()
                    flash("Perfil atualizado com sucesso.", "sucesso")
                    return redirect(url_for("perfil"))
                except sqlite3.IntegrityError:
                    db.rollback()
                    flash("Não foi possível salvar o perfil.", "erro")

    return render_template(
        "perfil.html",
        cliente=cliente,
        prestador=prestador,
    )


@app.route("/clientes")
@admin_required
def listar_clientes():
    db = get_db()
    clientes = db.execute(
        """
        SELECT u.id, u.nome, u.email, u.ativo, u.data_criacao,
               c.telefone, c.cidade
        FROM usuarios u
        LEFT JOIN clientes c ON c.usuario_id = u.id
        WHERE u.tipo = 'cliente'
        ORDER BY u.nome
        """
    ).fetchall()
    return render_template(
        "clientes.html",
        clientes=clientes,
        modo="listar",
    )


@app.route("/clientes/novo", methods=["GET", "POST"])
def novo_cliente():
    if request.method == "POST":
        nome = request.form.get("nome", "").strip()
        email = request.form.get("email", "").strip().lower()
        senha = request.form.get("senha", "")
        telefone = request.form.get("telefone", "").strip()
        cidade = request.form.get("cidade", "").strip()

        if not nome or not email or not senha:
            flash("Preencha todos os campos obrigatórios.", "erro")
            return render_template(
                "clientes.html",
                modo="novo",
                nome=nome,
                email=email,
                telefone=telefone,
                cidade=cidade,
            )

        if len(senha) < 8:
            flash("A senha deve ter pelo menos 8 caracteres.", "erro")
            return render_template(
                "clientes.html",
                modo="novo",
                nome=nome,
                email=email,
                telefone=telefone,
                cidade=cidade,
            )

        db = get_db()
        usuario_existente = db.execute(
            "SELECT id FROM usuarios WHERE email = ?",
            (email,),
        ).fetchone()

        if usuario_existente:
            flash("Este e-mail já está cadastrado.", "erro")
            return render_template(
                "clientes.html",
                modo="novo",
                nome=nome,
                email=email,
                telefone=telefone,
                cidade=cidade,
            )

        cursor = db.execute(
            """
            INSERT INTO usuarios (nome, email, senha_hash, tipo)
            VALUES (?, ?, ?, 'cliente')
            """,
            (nome, email, generate_password_hash(senha)),
        )
        db.execute(
            """
            INSERT INTO clientes (usuario_id, telefone, cidade)
            VALUES (?, ?, ?)
            """,
            (cursor.lastrowid, telefone, cidade),
        )
        db.commit()

        flash("Cadastro realizado com sucesso! Faça login.", "sucesso")
        if current_user.is_authenticated and current_user.tipo == "admin":
            return redirect(url_for("listar_clientes"))
        return redirect(url_for("login"))

    return render_template(
        "clientes.html",
        modo="novo",
        nome="",
        email="",
        telefone="",
        cidade="",
    )


@app.route("/clientes/<int:cliente_id>")
@admin_required
def consultar_cliente(cliente_id):
    db = get_db()
    cliente = db.execute(
        """
        SELECT u.id, u.nome, u.email, u.ativo, u.data_criacao,
               c.telefone, c.cidade
        FROM usuarios u
        LEFT JOIN clientes c ON c.usuario_id = u.id
        WHERE u.id = ? AND u.tipo = 'cliente'
        """,
        (cliente_id,),
    ).fetchone()
    if cliente is None:
        flash("Cliente não encontrado.", "erro")
        return redirect(url_for("listar_clientes"))
    return render_template(
        "clientes.html",
        cliente=cliente,
        modo="consultar",
    )


@app.route("/clientes/<int:cliente_id>/editar", methods=["GET", "POST"])
@admin_required
def editar_cliente(cliente_id):
    db = get_db()
    cliente = db.execute(
        """
        SELECT u.id, u.nome, u.email, u.ativo, u.data_criacao,
               c.telefone, c.cidade, c.id AS cliente_registro_id
        FROM usuarios u
        LEFT JOIN clientes c ON c.usuario_id = u.id
        WHERE u.id = ? AND u.tipo = 'cliente'
        """,
        (cliente_id,),
    ).fetchone()
    if cliente is None:
        flash("Cliente não encontrado.", "erro")
        return redirect(url_for("listar_clientes"))
    if cliente["ativo"] == 0:
        flash("Não é possível editar um cliente desativado.", "erro")
        return redirect(url_for("listar_clientes"))

    if request.method == "POST":
        nome = request.form.get("nome", "").strip()
        email = request.form.get("email", "").strip().lower()
        telefone = request.form.get("telefone", "").strip()
        cidade = request.form.get("cidade", "").strip()

        if not nome or not email:
            flash("Nome e e-mail são obrigatórios.", "erro")
        else:
            try:
                db.execute(
                    "UPDATE usuarios SET nome = ?, email = ? WHERE id = ?",
                    (nome, email, cliente_id),
                )
                existente = db.execute(
                    "SELECT id FROM clientes WHERE usuario_id = ?",
                    (cliente_id,),
                ).fetchone()
                if existente:
                    db.execute(
                        """
                        UPDATE clientes
                        SET telefone = ?, cidade = ?
                        WHERE usuario_id = ?
                        """,
                        (telefone, cidade, cliente_id),
                    )
                else:
                    db.execute(
                        """
                        INSERT INTO clientes (usuario_id, telefone, cidade)
                        VALUES (?, ?, ?)
                        """,
                        (cliente_id, telefone, cidade),
                    )
                db.commit()
                flash("Cliente atualizado com sucesso!", "sucesso")
                return redirect(url_for("listar_clientes"))
            except sqlite3.IntegrityError:
                db.rollback()
                flash("Este e-mail já está cadastrado.", "erro")

        return render_template(
            "clientes.html",
            cliente=cliente,
            modo="editar",
            nome=nome,
            email=email,
            telefone=telefone,
            cidade=cidade,
        )

    return render_template(
        "clientes.html",
        cliente=cliente,
        modo="editar",
        nome=cliente["nome"],
        email=cliente["email"],
        telefone=cliente["telefone"] or "",
        cidade=cliente["cidade"] or "",
    )


@app.route("/clientes/<int:cliente_id>/desativar", methods=["POST"])
@admin_required
def desativar_cliente(cliente_id):
    db = get_db()
    cliente = db.execute(
        """
        SELECT id, ativo FROM usuarios
        WHERE id = ? AND tipo = 'cliente'
        """,
        (cliente_id,),
    ).fetchone()

    if cliente is None:
        flash("Cliente não encontrado.", "erro")
    elif str(cliente_id) == current_user.id:
        flash("Não é possível desativar a própria conta.", "erro")
    elif cliente["ativo"] == 0:
        flash("Esse cliente já está desativado.", "erro")
    else:
        db.execute(
            "UPDATE usuarios SET ativo = 0 WHERE id = ?",
            (cliente_id,),
        )
        db.commit()
        flash("Cliente desativado com sucesso.", "sucesso")
    return redirect(url_for("listar_clientes"))


@app.route("/clientes/<int:cliente_id>/ativar", methods=["POST"])
@admin_required
def ativar_cliente(cliente_id):
    db = get_db()
    cliente = db.execute(
        """
        SELECT id, ativo FROM usuarios
        WHERE id = ? AND tipo = 'cliente'
        """,
        (cliente_id,),
    ).fetchone()

    if cliente is None:
        flash("Cliente não encontrado.", "erro")
    elif cliente["ativo"] == 1:
        flash("Esse cliente já está ativo.", "erro")
    else:
        db.execute(
            "UPDATE usuarios SET ativo = 1 WHERE id = ?",
            (cliente_id,),
        )
        db.commit()
        flash("Cliente reativado com sucesso.", "sucesso")
    return redirect(url_for("listar_clientes"))


@app.route("/categorias")
def listar_categorias():
    db = get_db()
    categorias = db.execute(
        """
        SELECT *
        FROM categorias
        ORDER BY nome
        """
    ).fetchall()
    return render_template(
        "categorias.html",
        categorias=categorias,
        modo="listar",
    )


@app.route("/categorias/nova", methods=["GET", "POST"])
@admin_required
def nova_categoria():
    if request.method == "POST":
        nome = request.form.get("nome", "").strip()
        descricao = request.form.get("descricao", "").strip()

        if not nome:
            flash("O nome da categoria é obrigatório.", "erro")
            return render_template(
                "categorias.html",
                categorias=[],
                modo="nova",
                nome=nome,
                descricao=descricao,
            )

        db = get_db()
        try:
            db.execute(
                """
                INSERT INTO categorias (nome, descricao)
                VALUES (?, ?)
                """,
                (nome, descricao),
            )
            db.commit()
            flash("Categoria cadastrada com sucesso!", "sucesso")
            return redirect(url_for("listar_categorias"))
        except sqlite3.IntegrityError:
            db.rollback()
            flash("Já existe uma categoria com esse nome.", "erro")
            return render_template(
                "categorias.html",
                categorias=[],
                modo="nova",
                nome=nome,
                descricao=descricao,
            )

    return render_template(
        "categorias.html",
        categorias=[],
        modo="nova",
        nome="",
        descricao="",
    )


@app.route("/categorias/<int:categoria_id>")
def consultar_categoria(categoria_id):
    db = get_db()
    categoria = db.execute(
        "SELECT * FROM categorias WHERE id = ?",
        (categoria_id,),
    ).fetchone()

    if categoria is None:
        flash("Categoria não encontrada.", "erro")
        return redirect(url_for("listar_categorias"))

    return render_template(
        "categorias.html",
        categorias=[],
        categoria=categoria,
        modo="consultar",
    )


@app.route("/categorias/<int:categoria_id>/editar", methods=["GET", "POST"])
@admin_required
def editar_categoria(categoria_id):
    db = get_db()
    categoria = db.execute(
        "SELECT * FROM categorias WHERE id = ?",
        (categoria_id,),
    ).fetchone()

    if categoria is None:
        flash("Categoria não encontrada.", "erro")
        return redirect(url_for("listar_categorias"))

    if categoria["ativo"] == 0:
        flash("Não é possível editar uma categoria desativada.", "erro")
        return redirect(url_for("listar_categorias"))

    if request.method == "POST":
        nome = request.form.get("nome", "").strip()
        descricao = request.form.get("descricao", "").strip()

        if not nome:
            flash("O nome da categoria é obrigatório.", "erro")
            return render_template(
                "categorias.html",
                categorias=[],
                categoria=categoria,
                modo="editar",
                nome=nome,
                descricao=descricao,
            )

        try:
            db.execute(
                """
                UPDATE categorias
                SET nome = ?, descricao = ?
                WHERE id = ?
                """,
                (nome, descricao, categoria_id),
            )
            db.commit()
            flash("Categoria atualizada com sucesso!", "sucesso")
            return redirect(url_for("listar_categorias"))
        except sqlite3.IntegrityError:
            db.rollback()
            flash("Já existe outra categoria com esse nome.", "erro")
            return render_template(
                "categorias.html",
                categorias=[],
                categoria=categoria,
                modo="editar",
                nome=nome,
                descricao=descricao,
            )

    return render_template(
        "categorias.html",
        categorias=[],
        categoria=categoria,
        modo="editar",
        nome=categoria["nome"],
        descricao=categoria["descricao"] or "",
    )


@app.route("/categorias/<int:categoria_id>/desativar", methods=["POST"])
@admin_required
def desativar_categoria(categoria_id):
    db = get_db()
    categoria = db.execute(
        "SELECT id, ativo FROM categorias WHERE id = ?",
        (categoria_id,),
    ).fetchone()

    if categoria is None:
        flash("Categoria não encontrada.", "erro")
    elif categoria["ativo"] == 0:
        flash("Essa categoria já está desativada.", "erro")
    else:
        db.execute(
            "UPDATE categorias SET ativo = 0 WHERE id = ?",
            (categoria_id,),
        )
        db.commit()
        flash("Categoria desativada com sucesso.", "sucesso")
    return redirect(url_for("listar_categorias"))


@app.route("/categorias/<int:categoria_id>/ativar", methods=["POST"])
@admin_required
def ativar_categoria(categoria_id):
    db = get_db()
    categoria = db.execute(
        "SELECT id, ativo FROM categorias WHERE id = ?",
        (categoria_id,),
    ).fetchone()

    if categoria is None:
        flash("Categoria não encontrada.", "erro")
    elif categoria["ativo"] == 1:
        flash("Essa categoria já está ativa.", "erro")
    else:
        db.execute(
            "UPDATE categorias SET ativo = 1 WHERE id = ?",
            (categoria_id,),
        )
        db.commit()
        flash("Categoria reativada com sucesso.", "sucesso")
    return redirect(url_for("listar_categorias"))


@app.route("/prestadores")
def listar_prestadores():
    db = get_db()
    if current_user.is_authenticated and current_user.tipo == "admin":
        prestadores = db.execute(
            "SELECT * FROM prestadores ORDER BY nome"
        ).fetchall()
    else:
        prestadores = db.execute(
            "SELECT * FROM prestadores WHERE ativo = 1 ORDER BY nome"
        ).fetchall()
    return render_template(
        "prestadores.html",
        prestadores=prestadores,
        modo="listar",
    )


@app.route("/prestadores/novo", methods=["GET", "POST"])
def novo_prestador():
    db = get_db()
    categorias = categorias_ativas(db)

    if request.method == "POST":
        nome = request.form.get("nome", "").strip()
        cpf = request.form.get("cpf", "").strip()
        email = request.form.get("email", "").strip().lower()
        telefone = request.form.get("telefone", "").strip()
        especialidade = request.form.get("especialidade", "").strip()
        senha = request.form.get("senha", "")
        categorias_selecionadas = request.form.getlist("categorias")

        contexto = dict(
            prestadores=[],
            modo="novo",
            nome=nome,
            cpf=cpf,
            email=email,
            telefone=telefone,
            especialidade=especialidade,
            categorias=categorias,
            categorias_selecionadas=categorias_selecionadas,
        )

        if not nome or not cpf or not email or not senha:
            flash("Nome, CPF, e-mail e senha são obrigatórios.", "erro")
            return render_template("prestadores.html", **contexto)

        if len(senha) < 8:
            flash("A senha deve ter pelo menos 8 caracteres.", "erro")
            return render_template("prestadores.html", **contexto)

        try:
            ids_selecionados = [
                int(id_categoria) for id_categoria in categorias_selecionadas
            ]
        except ValueError:
            flash("Seleção de serviços inválida.", "erro")
            contexto["categorias_selecionadas"] = []
            return render_template("prestadores.html", **contexto)

        ids_ativos = {categoria["id"] for categoria in categorias}
        if not set(ids_selecionados).issubset(ids_ativos):
            flash("Selecione apenas categorias ativas.", "erro")
            return render_template("prestadores.html", **contexto)

        try:
            prestador_existente = db.execute(
                """
                SELECT id FROM prestadores
                WHERE cpf = ? OR email = ?
                """,
                (cpf, email),
            ).fetchone()
            usuario_existente = db.execute(
                "SELECT id FROM usuarios WHERE email = ?",
                (email,),
            ).fetchone()

            if prestador_existente:
                flash("Já existe um prestador com esse CPF ou e-mail.", "erro")
                return render_template("prestadores.html", **contexto)

            if usuario_existente:
                flash("Este e-mail já está cadastrado.", "erro")
                return render_template("prestadores.html", **contexto)

            cursor_usuario = db.execute(
                """
                INSERT INTO usuarios (nome, email, senha_hash, tipo)
                VALUES (?, ?, ?, 'prestador')
                """,
                (nome, email, generate_password_hash(senha)),
            )
            usuario_id = cursor_usuario.lastrowid

            cursor = db.execute(
                """
                INSERT INTO prestadores
                (nome, cpf, email, telefone, especialidade, usuario_id)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (nome, cpf, email, telefone, especialidade, usuario_id),
            )
            registrar_areas_prestador(db, cursor.lastrowid, ids_selecionados)
            db.commit()
            flash("Prestador cadastrado com sucesso!", "sucesso")
            return redirect(url_for("listar_prestadores"))
        except sqlite3.IntegrityError:
            db.rollback()
            flash("Já existe um prestador com esse CPF ou e-mail.", "erro")
            return render_template("prestadores.html", **contexto)

    return render_template(
        "prestadores.html",
        prestadores=[],
        modo="novo",
        nome="",
        cpf="",
        email="",
        telefone="",
        especialidade="",
        categorias=categorias,
        categorias_selecionadas=[],
    )


@app.route("/prestadores/<int:prestador_id>")
def consultar_prestador(prestador_id):
    db = get_db()
    prestador = db.execute(
        "SELECT * FROM prestadores WHERE id = ?",
        (prestador_id,),
    ).fetchone()

    if prestador is None:
        flash("Prestador não encontrado.", "erro")
        return redirect(url_for("listar_prestadores"))

    if (
        not prestador["ativo"]
        and not (
            current_user.is_authenticated
            and (
                current_user.tipo == "admin"
                or pode_gerenciar_prestador(prestador)
            )
        )
    ):
        flash("Prestador não encontrado.", "erro")
        return redirect(url_for("listar_prestadores"))

    servicos_area = db.execute(
        """
        SELECT c.id, c.nome
        FROM prestador_servicos ps
        JOIN categorias c ON c.id = ps.categoria_id
        WHERE ps.prestador_id = ?
        ORDER BY c.nome
        """,
        (prestador_id,),
    ).fetchall()
    servicos = db.execute(
        """
        SELECT s.*, c.nome AS categoria_nome
        FROM servicos s
        JOIN categorias c ON c.id = s.categoria_id
        WHERE s.prestador_id = ?
          AND (s.ativo = 1 OR ? = 1)
        ORDER BY s.titulo
        """,
        (
            prestador_id,
            1
            if current_user.is_authenticated
            and (
                current_user.tipo == "admin"
                or pode_gerenciar_prestador(prestador)
            )
            else 0,
        ),
    ).fetchall()

    return render_template(
        "prestadores.html",
        prestadores=[],
        prestador=prestador,
        servicos=servicos_area,
        catalogo=servicos,
        modo="consultar",
    )


@app.route("/prestadores/<int:prestador_id>/editar", methods=["GET", "POST"])
@login_required
def editar_prestador(prestador_id):
    db = get_db()
    prestador = db.execute(
        "SELECT * FROM prestadores WHERE id = ?",
        (prestador_id,),
    ).fetchone()

    if prestador is None:
        flash("Prestador não encontrado.", "erro")
        return redirect(url_for("listar_prestadores"))

    if not pode_gerenciar_prestador(prestador):
        flash("Acesso não autorizado para este perfil.", "erro")
        return redirect(url_for("painel"))

    if not prestador["ativo"]:
        flash("Não é possível editar um prestador inativo.", "erro")
        return redirect(url_for("listar_prestadores"))

    categorias = db.execute(
        """
        SELECT c.id, c.nome, c.ativo
        FROM categorias c
        WHERE c.ativo = 1
           OR EXISTS (
                SELECT 1
                FROM prestador_servicos ps
                WHERE ps.categoria_id = c.id
                  AND ps.prestador_id = ?
           )
        ORDER BY c.nome
        """,
        (prestador_id,),
    ).fetchall()

    servicos_atuais = db.execute(
        """
        SELECT categoria_id
        FROM prestador_servicos
        WHERE prestador_id = ?
        """,
        (prestador_id,),
    ).fetchall()
    categorias_selecionadas = [
        str(servico["categoria_id"]) for servico in servicos_atuais
    ]

    if request.method == "POST":
        nome = request.form.get("nome", "").strip()
        cpf = request.form.get("cpf", "").strip()
        email = request.form.get("email", "").strip().lower()
        telefone = request.form.get("telefone", "").strip()
        especialidade = request.form.get("especialidade", "").strip()
        categorias_selecionadas = request.form.getlist("categorias")

        if not nome or not cpf or not email:
            flash("Nome, CPF e e-mail são obrigatórios.", "erro")
        else:
            try:
                ids_selecionados = [
                    int(categoria_id)
                    for categoria_id in categorias_selecionadas
                ]
                ids_disponiveis = {categoria["id"] for categoria in categorias}
                if not set(ids_selecionados).issubset(ids_disponiveis):
                    flash("Seleção de serviços inválida.", "erro")
                else:
                    try:
                        db.execute(
                            """
                            UPDATE prestadores
                            SET nome = ?, cpf = ?, email = ?,
                                telefone = ?, especialidade = ?
                            WHERE id = ?
                            """,
                            (
                                nome,
                                cpf,
                                email,
                                telefone,
                                especialidade,
                                prestador_id,
                            ),
                        )
                        sincronizar_usuario_prestador(
                            db, prestador, nome, email
                        )
                        registrar_areas_prestador(
                            db, prestador_id, ids_selecionados
                        )
                        db.commit()
                        flash("Prestador atualizado com sucesso!", "sucesso")
                        return redirect(url_for("listar_prestadores"))
                    except sqlite3.IntegrityError:
                        db.rollback()
                        flash(
                            "Esse CPF ou e-mail já pertence a outro prestador.",
                            "erro",
                        )
            except ValueError:
                flash("Seleção de serviços inválida.", "erro")

        prestador = {
            "id": prestador_id,
            "nome": nome,
            "cpf": cpf,
            "email": email,
            "telefone": telefone,
            "especialidade": especialidade,
            "ativo": 1,
        }
        return render_template(
            "prestadores.html",
            prestadores=[],
            prestador=prestador,
            modo="editar",
            nome=nome,
            cpf=cpf,
            email=email,
            telefone=telefone,
            especialidade=especialidade,
            categorias=categorias,
            categorias_selecionadas=categorias_selecionadas,
        )

    return render_template(
        "prestadores.html",
        prestadores=[],
        prestador=prestador,
        modo="editar",
        nome=prestador["nome"],
        cpf=prestador["cpf"],
        email=prestador["email"],
        telefone=prestador["telefone"] or "",
        especialidade=prestador["especialidade"] or "",
        categorias=categorias,
        categorias_selecionadas=categorias_selecionadas,
    )


@app.route("/prestadores/<int:prestador_id>/desativar", methods=["POST"])
@admin_required
def desativar_prestador(prestador_id):
    db = get_db()
    prestador = db.execute(
        "SELECT * FROM prestadores WHERE id = ?",
        (prestador_id,),
    ).fetchone()

    if prestador is None:
        flash("Prestador não encontrado.", "erro")
    elif not prestador["ativo"]:
        flash("Esse prestador já está inativo.", "erro")
    else:
        db.execute(
            "UPDATE prestadores SET ativo = 0 WHERE id = ?",
            (prestador_id,),
        )
        sincronizar_usuario_prestador(
            db, prestador, prestador["nome"], prestador["email"], ativo=0
        )
        db.commit()
        flash("Prestador desativado com sucesso.", "sucesso")
    return redirect(url_for("listar_prestadores"))


@app.route("/prestadores/<int:prestador_id>/ativar", methods=["POST"])
@admin_required
def ativar_prestador(prestador_id):
    db = get_db()
    prestador = db.execute(
        "SELECT * FROM prestadores WHERE id = ?",
        (prestador_id,),
    ).fetchone()

    if prestador is None:
        flash("Prestador não encontrado.", "erro")
        return redirect(url_for("listar_prestadores"))

    if prestador["ativo"]:
        flash("Este prestador já está ativo.", "erro")
        return redirect(url_for("listar_prestadores"))

    db.execute(
        "UPDATE prestadores SET ativo = 1 WHERE id = ?",
        (prestador_id,),
    )
    sincronizar_usuario_prestador(
        db, prestador, prestador["nome"], prestador["email"], ativo=1
    )
    db.commit()
    flash("Prestador reativado com sucesso!", "sucesso")
    return redirect(url_for("listar_prestadores"))


@app.route("/servicos")
def listar_servicos():
    db = get_db()
    termo = request.args.get("q", "").strip()
    categoria_id = request.args.get("categoria_id", "").strip()
    filtros = []
    params = []

    admin = current_user.is_authenticated and current_user.tipo == "admin"
    prestador = obter_prestador_atual(db)

    if admin:
        sql = """
            SELECT s.*, p.nome AS prestador_nome, c.nome AS categoria_nome
            FROM servicos s
            JOIN prestadores p ON p.id = s.prestador_id
            JOIN categorias c ON c.id = s.categoria_id
            WHERE 1 = 1
        """
    elif current_user.is_authenticated and current_user.tipo == "prestador" and prestador:
        sql = """
            SELECT s.*, p.nome AS prestador_nome, c.nome AS categoria_nome
            FROM servicos s
            JOIN prestadores p ON p.id = s.prestador_id
            JOIN categorias c ON c.id = s.categoria_id
            WHERE s.prestador_id = ?
        """
        params.append(prestador["id"])
    else:
        sql = """
            SELECT s.*, p.nome AS prestador_nome, c.nome AS categoria_nome
            FROM servicos s
            JOIN prestadores p ON p.id = s.prestador_id
            JOIN categorias c ON c.id = s.categoria_id
            WHERE s.ativo = 1 AND p.ativo = 1
        """

    if termo:
        filtros.append("(s.titulo LIKE ? OR s.descricao LIKE ? OR p.nome LIKE ?)")
        like = f"%{termo}%"
        params.extend([like, like, like])
    if categoria_id:
        filtros.append("s.categoria_id = ?")
        params.append(categoria_id)
    if filtros:
        sql += " AND " + " AND ".join(filtros)
    sql += " ORDER BY s.titulo"

    servicos = db.execute(sql, params).fetchall()
    categorias = categorias_ativas(db)
    return render_template(
        "servicos.html",
        servicos=servicos,
        categorias=categorias,
        modo="listar",
        termo=termo,
        categoria_id=categoria_id,
        prestador=prestador,
    )


@app.route("/servicos/novo", methods=["GET", "POST"])
@perfil_required("prestador", "admin")
def novo_servico():
    db = get_db()
    categorias = categorias_ativas(db)
    prestadores = db.execute(
        "SELECT id, nome FROM prestadores WHERE ativo = 1 ORDER BY nome"
    ).fetchall()
    prestador = obter_prestador_atual(db)

    if current_user.tipo == "prestador" and prestador is None:
        flash("Complete o cadastro profissional antes de oferecer serviços.", "erro")
        return redirect(url_for("perfil"))

    if request.method == "POST":
        titulo = request.form.get("titulo", "").strip()
        descricao = request.form.get("descricao", "").strip()
        preco_raw = request.form.get("preco", "").strip()
        categoria_sel = request.form.get("categoria_id", "").strip()
        prestador_sel = request.form.get("prestador_id", "").strip()

        if current_user.tipo == "prestador":
            prestador_id = prestador["id"]
        else:
            prestador_id = prestador_sel

        preco = None
        erro = None
        if not titulo or not categoria_sel or not prestador_id:
            erro = "Título, categoria e prestador são obrigatórios."
        else:
            try:
                categoria_id = int(categoria_sel)
                prestador_id = int(prestador_id)
            except ValueError:
                erro = "Seleção inválida."
            else:
                if preco_raw:
                    try:
                        preco = float(preco_raw.replace(",", "."))
                        if preco < 0:
                            erro = "O preço não pode ser negativo."
                    except ValueError:
                        erro = "Informe um preço válido."

        contexto = dict(
            modo="novo",
            categorias=categorias,
            prestadores=prestadores,
            titulo=titulo,
            descricao=descricao,
            preco=preco_raw,
            categoria_id=categoria_sel,
            prestador_id=str(prestador_id) if prestador_id else "",
            prestador=prestador,
        )
        if erro:
            flash(erro, "erro")
            return render_template("servicos.html", **contexto)

        categoria = db.execute(
            "SELECT id FROM categorias WHERE id = ? AND ativo = 1",
            (categoria_id,),
        ).fetchone()
        alvo = db.execute(
            "SELECT id FROM prestadores WHERE id = ? AND ativo = 1",
            (prestador_id,),
        ).fetchone()
        if categoria is None or alvo is None:
            flash("Categoria ou prestador inválido.", "erro")
            return render_template("servicos.html", **contexto)

        db.execute(
            """
            INSERT INTO servicos
            (prestador_id, categoria_id, titulo, descricao, preco)
            VALUES (?, ?, ?, ?, ?)
            """,
            (prestador_id, categoria_id, titulo, descricao, preco),
        )
        db.commit()
        flash("Serviço cadastrado com sucesso!", "sucesso")
        return redirect(url_for("listar_servicos"))

    return render_template(
        "servicos.html",
        modo="novo",
        categorias=categorias,
        prestadores=prestadores,
        titulo="",
        descricao="",
        preco="",
        categoria_id="",
        prestador_id=str(prestador["id"]) if prestador else "",
        prestador=prestador,
    )


@app.route("/servicos/<int:servico_id>")
def consultar_servico(servico_id):
    db = get_db()
    servico = db.execute(
        """
        SELECT s.*, p.nome AS prestador_nome, p.ativo AS prestador_ativo,
               c.nome AS categoria_nome
        FROM servicos s
        JOIN prestadores p ON p.id = s.prestador_id
        JOIN categorias c ON c.id = s.categoria_id
        WHERE s.id = ?
        """,
        (servico_id,),
    ).fetchone()
    if servico is None:
        flash("Serviço não encontrado.", "erro")
        return redirect(url_for("listar_servicos"))

    visivel = servico["ativo"] == 1 and servico["prestador_ativo"] == 1
    if not visivel and not pode_gerenciar_servico(servico):
        flash("Serviço não encontrado.", "erro")
        return redirect(url_for("listar_servicos"))

    return render_template(
        "servicos.html",
        modo="consultar",
        servico=servico,
    )


@app.route("/servicos/<int:servico_id>/editar", methods=["GET", "POST"])
@login_required
def editar_servico(servico_id):
    db = get_db()
    servico = db.execute(
        "SELECT * FROM servicos WHERE id = ?",
        (servico_id,),
    ).fetchone()
    if servico is None:
        flash("Serviço não encontrado.", "erro")
        return redirect(url_for("listar_servicos"))
    if not pode_gerenciar_servico(servico):
        flash("Acesso não autorizado para este perfil.", "erro")
        return redirect(url_for("painel"))
    if servico["ativo"] == 0:
        flash("Não é possível editar um serviço desativado.", "erro")
        return redirect(url_for("listar_servicos"))

    categorias = categorias_ativas(db)
    prestadores = db.execute(
        "SELECT id, nome FROM prestadores WHERE ativo = 1 ORDER BY nome"
    ).fetchall()
    prestador = obter_prestador_atual(db)

    if request.method == "POST":
        titulo = request.form.get("titulo", "").strip()
        descricao = request.form.get("descricao", "").strip()
        preco_raw = request.form.get("preco", "").strip()
        categoria_sel = request.form.get("categoria_id", "").strip()
        prestador_id = servico["prestador_id"]
        if current_user.tipo == "admin":
            prestador_sel = request.form.get("prestador_id", "").strip()
            if prestador_sel:
                prestador_id = prestador_sel

        preco = None
        erro = None
        if not titulo or not categoria_sel or not prestador_id:
            erro = "Título, categoria e prestador são obrigatórios."
        else:
            try:
                categoria_id = int(categoria_sel)
                prestador_id = int(prestador_id)
            except ValueError:
                erro = "Seleção inválida."
            else:
                if preco_raw:
                    try:
                        preco = float(preco_raw.replace(",", "."))
                        if preco < 0:
                            erro = "O preço não pode ser negativo."
                    except ValueError:
                        erro = "Informe um preço válido."
                else:
                    preco = None

        if erro:
            flash(erro, "erro")
        else:
            db.execute(
                """
                UPDATE servicos
                SET prestador_id = ?, categoria_id = ?, titulo = ?,
                    descricao = ?, preco = ?
                WHERE id = ?
                """,
                (
                    prestador_id,
                    categoria_id,
                    titulo,
                    descricao,
                    preco,
                    servico_id,
                ),
            )
            db.commit()
            flash("Serviço atualizado com sucesso!", "sucesso")
            return redirect(url_for("listar_servicos"))

        return render_template(
            "servicos.html",
            modo="editar",
            servico=servico,
            categorias=categorias,
            prestadores=prestadores,
            titulo=titulo,
            descricao=descricao,
            preco=preco_raw,
            categoria_id=categoria_sel,
            prestador_id=str(prestador_id),
            prestador=prestador,
        )

    return render_template(
        "servicos.html",
        modo="editar",
        servico=servico,
        categorias=categorias,
        prestadores=prestadores,
        titulo=servico["titulo"],
        descricao=servico["descricao"] or "",
        preco="" if servico["preco"] is None else servico["preco"],
        categoria_id=str(servico["categoria_id"]),
        prestador_id=str(servico["prestador_id"]),
        prestador=prestador,
    )


@app.route("/servicos/<int:servico_id>/desativar", methods=["POST"])
@login_required
def desativar_servico(servico_id):
    db = get_db()
    servico = db.execute(
        "SELECT * FROM servicos WHERE id = ?",
        (servico_id,),
    ).fetchone()
    if servico is None:
        flash("Serviço não encontrado.", "erro")
    elif not pode_gerenciar_servico(servico):
        flash("Acesso não autorizado para este perfil.", "erro")
        return redirect(url_for("painel"))
    elif servico["ativo"] == 0:
        flash("Esse serviço já está desativado.", "erro")
    else:
        db.execute(
            "UPDATE servicos SET ativo = 0 WHERE id = ?",
            (servico_id,),
        )
        db.commit()
        flash("Serviço desativado com sucesso.", "sucesso")
    return redirect(url_for("listar_servicos"))


@app.route("/servicos/<int:servico_id>/ativar", methods=["POST"])
@login_required
def ativar_servico(servico_id):
    db = get_db()
    servico = db.execute(
        "SELECT * FROM servicos WHERE id = ?",
        (servico_id,),
    ).fetchone()
    if servico is None:
        flash("Serviço não encontrado.", "erro")
    elif not pode_gerenciar_servico(servico):
        flash("Acesso não autorizado para este perfil.", "erro")
        return redirect(url_for("painel"))
    elif servico["ativo"] == 1:
        flash("Esse serviço já está ativo.", "erro")
    else:
        db.execute(
            "UPDATE servicos SET ativo = 1 WHERE id = ?",
            (servico_id,),
        )
        db.commit()
        flash("Serviço reativado com sucesso.", "sucesso")
    return redirect(url_for("listar_servicos"))


@app.route("/solicitacoes")
@login_required
def listar_solicitacoes():
    db = get_db()
    if current_user.tipo == "admin":
        solicitacoes = db.execute(
            """
            SELECT sol.*, s.titulo AS servico_titulo,
                   p.nome AS prestador_nome, u.nome AS cliente_nome
            FROM solicitacoes sol
            JOIN servicos s ON s.id = sol.servico_id
            JOIN prestadores p ON p.id = sol.prestador_id
            JOIN usuarios u ON u.id = sol.cliente_usuario_id
            ORDER BY sol.data_criacao DESC
            """
        ).fetchall()
    elif current_user.tipo == "prestador":
        prestador = obter_prestador_atual(db)
        if prestador is None:
            flash("Complete o cadastro profissional para ver solicitações.", "erro")
            return redirect(url_for("perfil"))
        solicitacoes = db.execute(
            """
            SELECT sol.*, s.titulo AS servico_titulo,
                   p.nome AS prestador_nome, u.nome AS cliente_nome
            FROM solicitacoes sol
            JOIN servicos s ON s.id = sol.servico_id
            JOIN prestadores p ON p.id = sol.prestador_id
            JOIN usuarios u ON u.id = sol.cliente_usuario_id
            WHERE sol.prestador_id = ?
            ORDER BY sol.data_criacao DESC
            """,
            (prestador["id"],),
        ).fetchall()
    else:
        solicitacoes = db.execute(
            """
            SELECT sol.*, s.titulo AS servico_titulo,
                   p.nome AS prestador_nome, u.nome AS cliente_nome
            FROM solicitacoes sol
            JOIN servicos s ON s.id = sol.servico_id
            JOIN prestadores p ON p.id = sol.prestador_id
            JOIN usuarios u ON u.id = sol.cliente_usuario_id
            WHERE sol.cliente_usuario_id = ?
            ORDER BY sol.data_criacao DESC
            """,
            (current_user.id,),
        ).fetchall()

    return render_template(
        "solicitacoes.html",
        solicitacoes=solicitacoes,
        modo="listar",
    )


@app.route("/solicitacoes/nova/<int:servico_id>", methods=["GET", "POST"])
@perfil_required("cliente")
def nova_solicitacao(servico_id):
    db = get_db()
    servico = db.execute(
        """
        SELECT s.*, p.nome AS prestador_nome, p.ativo AS prestador_ativo,
               c.nome AS categoria_nome
        FROM servicos s
        JOIN prestadores p ON p.id = s.prestador_id
        JOIN categorias c ON c.id = s.categoria_id
        WHERE s.id = ?
        """,
        (servico_id,),
    ).fetchone()
    if servico is None or servico["ativo"] != 1 or servico["prestador_ativo"] != 1:
        flash("Serviço indisponível para solicitação.", "erro")
        return redirect(url_for("listar_servicos"))

    if request.method == "POST":
        mensagem = request.form.get("mensagem", "").strip()
        db.execute(
            """
            INSERT INTO solicitacoes
            (cliente_usuario_id, servico_id, prestador_id, mensagem)
            VALUES (?, ?, ?, ?)
            """,
            (current_user.id, servico_id, servico["prestador_id"], mensagem),
        )
        db.commit()
        flash("Solicitação enviada com sucesso.", "sucesso")
        return redirect(url_for("listar_solicitacoes"))

    return render_template(
        "solicitacoes.html",
        modo="nova",
        servico=servico,
        mensagem="",
    )


def _obter_solicitacao(db, solicitacao_id):
    return db.execute(
        """
        SELECT sol.*, s.titulo AS servico_titulo,
               p.nome AS prestador_nome, u.nome AS cliente_nome
        FROM solicitacoes sol
        JOIN servicos s ON s.id = sol.servico_id
        JOIN prestadores p ON p.id = sol.prestador_id
        JOIN usuarios u ON u.id = sol.cliente_usuario_id
        WHERE sol.id = ?
        """,
        (solicitacao_id,),
    ).fetchone()


@app.route("/solicitacoes/<int:solicitacao_id>/<acao>", methods=["POST"])
@login_required
def atualizar_solicitacao(solicitacao_id, acao):
    db = get_db()
    solicitacao = _obter_solicitacao(db, solicitacao_id)
    if solicitacao is None:
        flash("Solicitação não encontrada.", "erro")
        return redirect(url_for("listar_solicitacoes"))

    transicoes = {
        "cancelar": ("cancelada", "pendente"),
        "aceitar": ("aceita", "pendente"),
        "recusar": ("recusada", "pendente"),
        "concluir": ("concluida", "aceita"),
    }
    if acao not in transicoes:
        flash("Ação inválida.", "erro")
        return redirect(url_for("listar_solicitacoes"))

    novo_status, status_atual = transicoes[acao]
    prestador = obter_prestador_atual(db)
    permitido = False

    if acao == "cancelar":
        permitido = (
            current_user.tipo == "cliente"
            and str(solicitacao["cliente_usuario_id"]) == current_user.id
        )
    elif acao in ("aceitar", "recusar", "concluir"):
        permitido = (
            current_user.tipo == "prestador"
            and prestador is not None
            and prestador["id"] == solicitacao["prestador_id"]
        ) or current_user.tipo == "admin"

    if not permitido:
        flash("Acesso não autorizado para este perfil.", "erro")
        return redirect(url_for("listar_solicitacoes"))

    if solicitacao["status"] != status_atual:
        flash("Esta solicitação não pode ser atualizada agora.", "erro")
        return redirect(url_for("listar_solicitacoes"))

    db.execute(
        "UPDATE solicitacoes SET status = ? WHERE id = ?",
        (novo_status, solicitacao_id),
    )
    db.commit()
    flash("Solicitação atualizada com sucesso.", "sucesso")
    return redirect(url_for("listar_solicitacoes"))


@app.route("/acesso-negado")
def acesso_negado():
    flash("Acesso não autorizado para este perfil.", "erro")
    return redirect(url_for("inicio"))


if __name__ == "__main__":
    app.run(debug=True)
