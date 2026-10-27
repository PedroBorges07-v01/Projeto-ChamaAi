from flask import Flask, render_template, request, redirect, url_for, flash
import sqlite3

from database import get_db, init_app


app = Flask(__name__)

# Chave para utilizar mensagens temporárias do Flask.
# Em produção, utilize uma chave secreta configurada de forma segura.
app.config["SECRET_KEY"] = "chave-desenvolvimento-local"

# Configura o banco e cria a tabela, caso ela não exista.
init_app(app)
app.config["TESTING"] = False


@app.route("/")
def inicio():
    return render_template("index.html")


@app.route("/categorias")
def listar_categorias():
    db = get_db()

    categorias = db.execute("""
        SELECT *
        FROM categorias
        ORDER BY nome
    """).fetchall()

    return render_template(
        "categorias.html",
        categorias=categorias,
        modo="listar"
    )


@app.route("/categorias/nova", methods=["GET", "POST"])
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
                descricao=descricao
            )

        db = get_db()

        try:
            db.execute("""
                INSERT INTO categorias (nome, descricao)
                VALUES (?, ?)
            """, (nome, descricao))

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
                descricao=descricao
            )

    return render_template(
        "categorias.html",
        categorias=[],
        modo="nova",
        nome="",
        descricao=""
    )


@app.route("/categorias/<int:categoria_id>")
def consultar_categoria(categoria_id):
    db = get_db()

    categoria = db.execute("""
        SELECT *
        FROM categorias
        WHERE id = ?
    """, (categoria_id,)).fetchone()

    if categoria is None:
        flash("Categoria não encontrada.", "erro")
        return redirect(url_for("listar_categorias"))

    return render_template(
        "categorias.html",
        categorias=[],
        categoria=categoria,
        modo="consultar"
    )


@app.route("/categorias/<int:categoria_id>/editar", methods=["GET", "POST"])
def editar_categoria(categoria_id):
    db = get_db()

    categoria = db.execute("""
        SELECT *
        FROM categorias
        WHERE id = ?
    """, (categoria_id,)).fetchone()

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
                descricao=descricao
            )

        try:
            db.execute("""
                UPDATE categorias
                SET nome = ?, descricao = ?
                WHERE id = ?
            """, (nome, descricao, categoria_id))

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
                descricao=descricao
            )

    return render_template(
        "categorias.html",
        categorias=[],
        categoria=categoria,
        modo="editar",
        nome=categoria["nome"],
        descricao=categoria["descricao"] or ""
    )


@app.route("/categorias/<int:categoria_id>/desativar", methods=["POST"])
def desativar_categoria(categoria_id):
    db = get_db()

    categoria = db.execute("""
        SELECT id, ativo
        FROM categorias
        WHERE id = ?
    """, (categoria_id,)).fetchone()

    if categoria is None:
        flash("Categoria não encontrada.", "erro")

    elif categoria["ativo"] == 0:
        flash("Essa categoria já está desativada.", "erro")

    else:
        db.execute("""
            UPDATE categorias
            SET ativo = 0
            WHERE id = ?
        """, (categoria_id,))

        db.commit()

        flash("Categoria desativada com sucesso.", "sucesso")

    return redirect(url_for("listar_categorias"))


@app.route("/prestadores")
def listar_prestadores():
    db = get_db()
    prestadores = db.execute("""
        SELECT * FROM prestadores ORDER BY nome
    """).fetchall()
    return render_template(
        "prestadores.html",
        prestadores=prestadores,
        modo="listar"
    )


@app.route("/prestadores/novo", methods=["GET", "POST"])
def novo_prestador():
    if request.method == "POST":
        nome = request.form.get("nome", "").strip()
        cpf = request.form.get("cpf", "").strip()
        email = request.form.get("email", "").strip().lower()
        telefone = request.form.get("telefone", "").strip()
        especialidade = request.form.get("especialidade", "").strip()

        if not nome or not cpf or not email:
            flash("Nome, CPF e e-mail são obrigatórios.", "erro")
            return render_template(
                "prestadores.html",
                prestadores=[],
                modo="novo",
                nome=nome,
                cpf=cpf,
                email=email,
                telefone=telefone,
                especialidade=especialidade
            )

        db = get_db()
        try:
            db.execute("""
                INSERT INTO prestadores
                (nome, cpf, email, telefone, especialidade)
                VALUES (?, ?, ?, ?, ?)
            """, (nome, cpf, email, telefone, especialidade))
            db.commit()
            flash("Prestador cadastrado com sucesso!", "sucesso")
            return redirect(url_for("listar_prestadores"))
        except sqlite3.IntegrityError:
            db.rollback()
            flash("Já existe um prestador com esse CPF ou e-mail.", "erro")
            return render_template(
                "prestadores.html",
                prestadores=[],
                modo="novo",
                nome=nome,
                cpf=cpf,
                email=email,
                telefone=telefone,
                especialidade=especialidade
            )

    return render_template(
        "prestadores.html",
        prestadores=[],
        modo="novo",
        nome="",
        cpf="",
        email="",
        telefone="",
        especialidade=""
    )


@app.route("/prestadores/<int:prestador_id>")
def consultar_prestador(prestador_id):
    db = get_db()
    prestador = db.execute(
        "SELECT * FROM prestadores WHERE id = ?",
        (prestador_id,)
    ).fetchone()

    if prestador is None:
        flash("Prestador não encontrado.", "erro")
        return redirect(url_for("listar_prestadores"))

    return render_template(
        "prestadores.html",
        prestadores=[],
        prestador=prestador,
        modo="consultar"
    )


@app.route("/prestadores/<int:prestador_id>/editar",
           methods=["GET", "POST"])
def editar_prestador(prestador_id):
    db = get_db()
    prestador = db.execute(
        "SELECT * FROM prestadores WHERE id = ?",
        (prestador_id,)
    ).fetchone()

    if prestador is None:
        flash("Prestador não encontrado.", "erro")
        return redirect(url_for("listar_prestadores"))

    if not prestador["ativo"]:
        flash("Não é possível editar um prestador inativo.", "erro")
        return redirect(url_for("listar_prestadores"))

    if request.method == "POST":
        nome = request.form.get("nome", "").strip()
        cpf = request.form.get("cpf", "").strip()
        email = request.form.get("email", "").strip().lower()
        telefone = request.form.get("telefone", "").strip()
        especialidade = request.form.get("especialidade", "").strip()

        if not nome or not cpf or not email:
            flash("Nome, CPF e e-mail são obrigatórios.", "erro")
            return render_template(
                "prestadores.html",
                prestadores=[],
                prestador=prestador,
                modo="editar",
                nome=nome,
                cpf=cpf,
                email=email,
                telefone=telefone,
                especialidade=especialidade
            )

        try:
            db.execute("""
                UPDATE prestadores
                SET nome = ?, cpf = ?, email = ?,
                    telefone = ?, especialidade = ?
                WHERE id = ?
            """, (
                nome, cpf, email, telefone,
                especialidade, prestador_id
            ))
            db.commit()
            flash("Prestador atualizado com sucesso!", "sucesso")
            return redirect(url_for("listar_prestadores"))
        except sqlite3.IntegrityError:
            db.rollback()
            flash("Esse CPF ou e-mail já pertence a outro prestador.", "erro")
            return render_template(
                "prestadores.html",
                prestadores=[],
                prestador=prestador,
                modo="editar",
                nome=nome,
                cpf=cpf,
                email=email,
                telefone=telefone,
                especialidade=especialidade
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
        especialidade=prestador["especialidade"] or ""
    )


@app.route("/prestadores/<int:prestador_id>/desativar",
           methods=["POST"])
def desativar_prestador(prestador_id):
    db = get_db()
    prestador = db.execute(
        "SELECT id, ativo FROM prestadores WHERE id = ?",
        (prestador_id,)
    ).fetchone()

    if prestador is None:
        flash("Prestador não encontrado.", "erro")
    elif not prestador["ativo"]:
        flash("Esse prestador já está inativo.", "erro")
    else:
        db.execute(
            "UPDATE prestadores SET ativo = 0 WHERE id = ?",
            (prestador_id,)
        )
        db.commit()
        flash("Prestador desativado com sucesso.", "sucesso")

    return redirect(url_for("listar_prestadores"))


if __name__ == "__main__":
    app.run(debug=True)