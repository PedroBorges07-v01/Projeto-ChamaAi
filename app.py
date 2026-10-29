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

@app.route("/categorias/<int:categoria_id>/ativar", methods=["POST"])
def ativar_categoria(categoria_id):
    db = get_db()

    categoria = db.execute("""
        SELECT id, ativo
        FROM categorias
        WHERE id = ?
    """, (categoria_id,)).fetchone()

    if categoria is None:
        flash("Categoria não encontrada.", "erro")

    elif categoria["ativo"] == 1:
        flash("Essa categoria já está ativa.", "erro")

    else:
        db.execute("""
            UPDATE categorias
            SET ativo = 1
            WHERE id = ?
        """, (categoria_id,))

        db.commit()

        flash("Categoria reativada com sucesso.", "sucesso")

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
    db = get_db()

    categorias = db.execute("""
        SELECT id, nome, ativo
        FROM categorias
        WHERE ativo = 1
        ORDER BY nome
    """).fetchall()

    if request.method == "POST":
        nome = request.form.get("nome", "").strip()
        cpf = request.form.get("cpf", "").strip()
        email = request.form.get("email", "").strip().lower()
        telefone = request.form.get("telefone", "").strip()
        especialidade = request.form.get("especialidade", "").strip()

        categorias_selecionadas = request.form.getlist("categorias")

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
                especialidade=especialidade,
                categorias=categorias,
                categorias_selecionadas=categorias_selecionadas
            )

        try:
            ids_selecionados = [int(id_categoria)
                                for id_categoria in categorias_selecionadas]
        except ValueError:
            flash("Seleção de serviços inválida.", "erro")
            return render_template(
                "prestadores.html",
                prestadores=[],
                modo="novo",
                nome=nome,
                cpf=cpf,
                email=email,
                telefone=telefone,
                especialidade=especialidade,
                categorias=categorias,
                categorias_selecionadas=[]
            )

        ids_ativos = {categoria["id"] for categoria in categorias}

        if not set(ids_selecionados).issubset(ids_ativos):
            flash("Selecione apenas categorias ativas.", "erro")
            return render_template(
                "prestadores.html",
                prestadores=[],
                modo="novo",
                nome=nome,
                cpf=cpf,
                email=email,
                telefone=telefone,
                especialidade=especialidade,
                categorias=categorias,
                categorias_selecionadas=categorias_selecionadas
            )

        try:
            cursor = db.execute("""
                INSERT INTO prestadores
                (nome, cpf, email, telefone, especialidade)
                VALUES (?, ?, ?, ?, ?)
            """, (nome, cpf, email, telefone, especialidade))

            prestador_id = cursor.lastrowid

            for categoria_id in set(ids_selecionados):
                db.execute("""
                    INSERT INTO prestador_servicos
                    (prestador_id, categoria_id)
                    VALUES (?, ?)
                """, (prestador_id, categoria_id))

            db.commit()
            flash("Prestador cadastrado com sucesso!", "sucesso")
            return redirect(url_for("listar_prestadores"))

        except sqlite3.IntegrityError:
            db.rollback()
            flash(
                "Já existe um prestador com esse CPF ou e-mail.",
                "erro"
            )
            return render_template(
                "prestadores.html",
                prestadores=[],
                modo="novo",
                nome=nome,
                cpf=cpf,
                email=email,
                telefone=telefone,
                especialidade=especialidade,
                categorias=categorias,
                categorias_selecionadas=categorias_selecionadas
            )

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
        categorias_selecionadas=[]
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

    servicos = db.execute("""
        SELECT c.id, c.nome
        FROM prestador_servicos ps
        JOIN categorias c ON c.id = ps.categoria_id
        WHERE ps.prestador_id = ?
        ORDER BY c.nome
    """, (prestador_id,)).fetchall()

    return render_template(
        "prestadores.html",
        prestadores=[],
        prestador=prestador,
        servicos=servicos,
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

    # Busca categorias ativas e categorias já vinculadas
    # a este prestador, mesmo que estejam inativas.
    categorias = db.execute("""
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
    """, (prestador_id,)).fetchall()


    # Recupera os serviços que o prestador já oferece.
    servicos_atuais = db.execute("""
        SELECT categoria_id
        FROM prestador_servicos
        WHERE prestador_id = ?
    """, (prestador_id,)).fetchall()

    categorias_selecionadas = [
        str(servico["categoria_id"])
        for servico in servicos_atuais
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

                ids_disponiveis = {
                    categoria["id"] for categoria in categorias
                }

                if not set(ids_selecionados).issubset(ids_disponiveis):
                    flash("Seleção de serviços inválida.", "erro")

                else:
                    # Inicia uma transação para salvar tudo em conjunto.
                    try:
                        db.execute("""
                            UPDATE prestadores
                            SET nome = ?, cpf = ?, email = ?,
                                telefone = ?, especialidade = ?
                            WHERE id = ?
                        """, (
                            nome,
                            cpf,
                            email,
                            telefone,
                            especialidade,
                            prestador_id
                        ))

                        # Substitui os vínculos pelos serviços selecionados.
                        db.execute("""
                            DELETE FROM prestador_servicos
                            WHERE prestador_id = ?
                        """, (prestador_id,))

                        for categoria_id in set(ids_selecionados):
                            db.execute("""
                                INSERT INTO prestador_servicos
                                (prestador_id, categoria_id)
                                VALUES (?, ?)
                            """, (prestador_id, categoria_id))

                        db.commit()

                        flash(
                            "Prestador atualizado com sucesso!",
                            "sucesso"
                        )
                        return redirect(url_for("listar_prestadores"))

                    except sqlite3.IntegrityError:
                        db.rollback()
                        flash(
                            "Esse CPF ou e-mail já pertence a outro prestador.",
                            "erro"
                        )

            except ValueError:
                flash("Seleção de serviços inválida.", "erro")

        # Atualiza o prestador para exibir os dados enviados no formulário.
        prestador = {
            "id": prestador_id,
            "nome": nome,
            "cpf": cpf,
            "email": email,
            "telefone": telefone,
            "especialidade": especialidade,
            "ativo": 1
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
            categorias_selecionadas=categorias_selecionadas
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
        categorias_selecionadas=categorias_selecionadas
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


@app.route("/prestadores/<int:prestador_id>/ativar", methods=["POST"])
def ativar_prestador(prestador_id):
    db = get_db()

    prestador = db.execute(
        "SELECT id, ativo FROM prestadores WHERE id = ?",
        (prestador_id,)
    ).fetchone()

    if prestador is None:
        flash("Prestador não encontrado.", "erro")
        return redirect(url_for("listar_prestadores"))

    if prestador["ativo"]:
        flash("Este prestador já está ativo.", "erro")
        return redirect(url_for("listar_prestadores"))

    db.execute(
        "UPDATE prestadores SET ativo = 1 WHERE id = ?",
        (prestador_id,)
    )
    db.commit()

    flash("Prestador reativado com sucesso!", "sucesso")
    return redirect(url_for("listar_prestadores"))



if __name__ == "__main__":
    app.run(debug=True)