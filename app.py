from functools import wraps
import os
import sqlite3
import uuid

import click
from flask import (
    Flask,
    abort,
    flash,
    redirect,
    render_template,
    request,
    send_from_directory,
    url_for,
)
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
app.config["MAX_CONTENT_LENGTH"] = 5 * 1024 * 1024  # 5 MB por envio
app.config["UPLOAD_FOLDER"] = os.path.join(app.instance_path, "uploads")

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
            "categorias": db.execute(
                "SELECT COUNT(*) AS total FROM categorias"
            ).fetchone()["total"],
            "pedidos": db.execute(
                "SELECT COUNT(*) AS total FROM pedidos"
            ).fetchone()["total"],
        }
        return render_template("painel.html", resumo=resumo)

    if current_user.tipo == "prestador":
        prestador = obter_prestador_atual(db)
        return render_template("painel.html", prestador=prestador)

    return render_template("painel.html")


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


@app.route("/clientes/<int:cliente_id>/remover", methods=["POST"])
@admin_required
def remover_cliente(cliente_id):
    db = get_db()
    cliente = db.execute(
        """
        SELECT id FROM usuarios
        WHERE id = ? AND tipo = 'cliente'
        """,
        (cliente_id,),
    ).fetchone()

    if cliente is None:
        flash("Cliente não encontrado.", "erro")
    elif str(cliente_id) == current_user.id:
        flash("Não é possível remover a própria conta.", "erro")
    else:
        total = db.execute(
            "SELECT COUNT(*) FROM pedidos WHERE cliente_usuario_id = ?",
            (cliente_id,),
        ).fetchone()[0]
        if total:
            flash(
                "Este cliente possui pedidos registrados e não pode "
                "ser removido. Use a opção Desativar.",
                "erro",
            )
        else:
            db.execute("DELETE FROM clientes WHERE usuario_id = ?", (cliente_id,))
            db.execute("DELETE FROM usuarios WHERE id = ?", (cliente_id,))
            db.commit()
            flash("Cliente removido com sucesso.", "sucesso")
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


@app.route("/categorias/<int:categoria_id>/remover", methods=["POST"])
@admin_required
def remover_categoria(categoria_id):
    db = get_db()
    categoria = db.execute(
        "SELECT id FROM categorias WHERE id = ?",
        (categoria_id,),
    ).fetchone()

    if categoria is None:
        flash("Categoria não encontrada.", "erro")
    else:
        total = db.execute(
            "SELECT COUNT(*) FROM pedidos WHERE categoria_id = ?",
            (categoria_id,),
        ).fetchone()[0]
        if total:
            flash(
                "Esta categoria possui pedidos cadastrados e não pode "
                "ser removida. Use a opção Desativar.",
                "erro",
            )
        else:
            db.execute(
                "DELETE FROM prestador_servicos WHERE categoria_id = ?",
                (categoria_id,),
            )
            db.execute("DELETE FROM categorias WHERE id = ?", (categoria_id,))
            db.commit()
            flash("Categoria removida com sucesso.", "sucesso")
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
    return render_template(
        "prestadores.html",
        prestadores=[],
        prestador=prestador,
        servicos=servicos_area,
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


@app.route("/prestadores/<int:prestador_id>/remover", methods=["POST"])
@admin_required
def remover_prestador(prestador_id):
    db = get_db()
    prestador = db.execute(
        "SELECT * FROM prestadores WHERE id = ?",
        (prestador_id,),
    ).fetchone()

    if prestador is None:
        flash("Prestador não encontrado.", "erro")
    else:
        total = db.execute(
            "SELECT COUNT(*) FROM pedidos WHERE prestador_id = ?",
            (prestador_id,),
        ).fetchone()[0]
        if total:
            flash(
                "Este prestador possui pedidos registrados e não pode "
                "ser removido. Use a opção Desativar.",
                "erro",
            )
        else:
            usuario = db.execute(
                """
                SELECT id FROM usuarios
                WHERE tipo = 'prestador' AND (id = ? OR email = ?)
                """,
                (prestador["usuario_id"], prestador["email"]),
            ).fetchone()

            db.execute(
                "DELETE FROM prestador_servicos WHERE prestador_id = ?",
                (prestador_id,),
            )
            db.execute(
                "DELETE FROM pedido_recusas WHERE prestador_id = ?",
                (prestador_id,),
            )
            db.execute("DELETE FROM prestadores WHERE id = ?", (prestador_id,))
            if usuario is not None:
                db.execute("DELETE FROM usuarios WHERE id = ?", (usuario["id"],))
            db.commit()
            flash("Prestador removido com sucesso.", "sucesso")
    return redirect(url_for("listar_prestadores"))


def _extensao_imagem(dados):
    """Identifica o tipo real da imagem pelo conteúdo (não só pelo nome)."""
    if dados.startswith(b"\xff\xd8\xff"):
        return ".jpg"
    if dados.startswith(b"\x89PNG\r\n\x1a\n"):
        return ".png"
    if dados[:6] in (b"GIF87a", b"GIF89a"):
        return ".gif"
    if dados[:4] == b"RIFF" and dados[8:12] == b"WEBP":
        return ".webp"
    return None


@app.errorhandler(413)
def arquivo_muito_grande(e):
    flash("A foto deve ter no máximo 5 MB.", "erro")
    return redirect(url_for("novo_pedido"))


@app.route("/pedidos")
@login_required
def listar_pedidos():
    db = get_db()
    base_sql = """
        SELECT p.*, c.nome AS categoria_nome, u.nome AS cliente_nome,
               pr.nome AS prestador_nome
        FROM pedidos p
        JOIN categorias c ON c.id = p.categoria_id
        JOIN usuarios u ON u.id = p.cliente_usuario_id
        LEFT JOIN prestadores pr ON pr.id = p.prestador_id
    """
    ordem = " ORDER BY p.data_criacao DESC, p.id DESC"

    if current_user.tipo == "admin":
        pedidos = db.execute(base_sql + ordem).fetchall()
    elif current_user.tipo == "prestador":
        prestador = obter_prestador_atual(db)
        if prestador is None:
            flash("Complete o cadastro profissional para ver pedidos.", "erro")
            return redirect(url_for("perfil"))
        pedidos = db.execute(
            base_sql
            + """
            WHERE (
                p.status = 'aberto'
                AND p.id NOT IN (
                    SELECT pedido_id FROM pedido_recusas WHERE prestador_id = ?
                )
            ) OR p.prestador_id = ?
            """
            + ordem,
            (prestador["id"], prestador["id"]),
        ).fetchall()
    else:
        pedidos = db.execute(
            base_sql + " WHERE p.cliente_usuario_id = ?" + ordem,
            (current_user.id,),
        ).fetchall()

    return render_template("pedidos.html", modo="listar", pedidos=pedidos)


@app.route("/pedidos/novo", methods=["GET", "POST"])
@perfil_required("cliente")
def novo_pedido():
    db = get_db()
    categorias = categorias_ativas(db)

    if request.method == "POST":
        categoria_sel = request.form.get("categoria_id", "").strip()
        descricao = request.form.get("descricao", "").strip()
        arquivo = request.files.get("foto")
        erros = []

        categoria = None
        if categoria_sel.isdigit():
            categoria = db.execute(
                "SELECT id FROM categorias WHERE id = ? AND ativo = 1",
                (int(categoria_sel),),
            ).fetchone()
        if categoria is None:
            erros.append("Selecione o tipo de serviço.")

        if not descricao:
            erros.append("Informe a descrição do serviço.")
        elif len(descricao) > 2000:
            erros.append("A descrição deve ter no máximo 2000 caracteres.")

        dados = None
        extensao = None
        if arquivo is not None and arquivo.filename:
            dados = arquivo.read()
            extensao = _extensao_imagem(dados)
            if extensao is None:
                erros.append("A foto deve ser uma imagem JPG, PNG, GIF ou WEBP.")

        if not erros:
            nome_foto = None
            if dados is not None:
                pasta = app.config["UPLOAD_FOLDER"]
                os.makedirs(pasta, exist_ok=True)
                nome_foto = uuid.uuid4().hex + extensao
                with open(os.path.join(pasta, nome_foto), "wb") as destino:
                    destino.write(dados)

            db.execute(
                """
                INSERT INTO pedidos
                (cliente_usuario_id, categoria_id, descricao, foto)
                VALUES (?, ?, ?, ?)
                """,
                (current_user.id, int(categoria_sel), descricao, nome_foto),
            )
            db.commit()
            flash("Pedido enviado com sucesso.", "sucesso")
            return redirect(url_for("listar_pedidos"))

        for erro in erros:
            flash(erro, "erro")
        return render_template(
            "pedidos.html",
            modo="novo",
            categorias=categorias,
            categoria_id=categoria_sel,
            descricao=descricao,
        )

    return render_template(
        "pedidos.html",
        modo="novo",
        categorias=categorias,
        categoria_id="",
        descricao="",
    )


@app.route("/pedidos/<int:pedido_id>/foto")
@login_required
def foto_pedido(pedido_id):
    db = get_db()
    pedido = db.execute(
        "SELECT cliente_usuario_id, foto FROM pedidos WHERE id = ?",
        (pedido_id,),
    ).fetchone()
    if pedido is None or not pedido["foto"]:
        abort(404)

    dono = str(pedido["cliente_usuario_id"]) == current_user.id
    if not (dono or current_user.tipo in ("admin", "prestador")):
        abort(403)

    resposta = send_from_directory(app.config["UPLOAD_FOLDER"], pedido["foto"])
    resposta.headers["X-Content-Type-Options"] = "nosniff"
    return resposta


@app.route("/pedidos/<int:pedido_id>/<acao>", methods=["POST"])
@login_required
def atualizar_pedido(pedido_id, acao):
    db = get_db()
    pedido = db.execute(
        "SELECT * FROM pedidos WHERE id = ?",
        (pedido_id,),
    ).fetchone()
    if pedido is None:
        flash("Pedido não encontrado.", "erro")
        return redirect(url_for("listar_pedidos"))

    if acao not in ("aceitar", "recusar", "cancelar"):
        flash("Ação inválida.", "erro")
        return redirect(url_for("listar_pedidos"))

    if acao == "cancelar":
        if (
            current_user.tipo != "cliente"
            or str(pedido["cliente_usuario_id"]) != current_user.id
        ):
            flash("Acesso não autorizado para este perfil.", "erro")
            return redirect(url_for("listar_pedidos"))
        cursor = db.execute(
            "UPDATE pedidos SET status = 'cancelado' "
            "WHERE id = ? AND status = 'aberto'",
            (pedido_id,),
        )
        db.commit()
        if cursor.rowcount:
            flash("Pedido cancelado.", "sucesso")
        else:
            flash("Este pedido não pode ser cancelado agora.", "erro")
        return redirect(url_for("listar_pedidos"))

    prestador = obter_prestador_atual(db)
    if (
        current_user.tipo != "prestador"
        or prestador is None
        or not prestador["ativo"]
    ):
        flash("Acesso não autorizado para este perfil.", "erro")
        return redirect(url_for("listar_pedidos"))

    if acao == "aceitar":
        # UPDATE condicional: só um prestador consegue aceitar o pedido.
        cursor = db.execute(
            """
            UPDATE pedidos
            SET status = 'aceito', prestador_id = ?
            WHERE id = ? AND status = 'aberto'
            """,
            (prestador["id"], pedido_id),
        )
        db.commit()
        if cursor.rowcount:
            flash("Pedido aceito com sucesso.", "sucesso")
        else:
            flash("Este pedido não está mais disponível.", "erro")
    else:
        if pedido["status"] != "aberto":
            flash("Este pedido não está mais disponível.", "erro")
        else:
            db.execute(
                """
                INSERT OR IGNORE INTO pedido_recusas (pedido_id, prestador_id)
                VALUES (?, ?)
                """,
                (pedido_id, prestador["id"]),
            )
            db.commit()
            flash("Pedido recusado. Ele não aparecerá mais para você.", "sucesso")
    return redirect(url_for("listar_pedidos"))


@app.route("/acesso-negado")
def acesso_negado():
    flash("Acesso não autorizado para este perfil.", "erro")
    return redirect(url_for("inicio"))


if __name__ == "__main__":
    app.run(debug=True)