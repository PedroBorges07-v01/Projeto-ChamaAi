(function () {
    var raiz = document.documentElement;

    /* Modo escuro */
    var btnTema = document.getElementById('tema-toggle');
    if (btnTema) {
        btnTema.addEventListener('click', function () {
            var novo = raiz.getAttribute('data-theme') === 'dark' ? 'light' : 'dark';
            raiz.setAttribute('data-theme', novo);
            try { localStorage.setItem('tema', novo); } catch (e) {}
        });
    }

    /* Painel de suporte */
    var abrir = document.getElementById('suporte-abrir');
    var fechar = document.getElementById('suporte-fechar');
    var painel = document.getElementById('suporte-painel');

    function mostrar(aberto) {
        painel.hidden = !aberto;
        abrir.setAttribute('aria-expanded', String(aberto));
    }

    if (abrir && painel) {
        abrir.addEventListener('click', function () { mostrar(painel.hidden); });
        if (fechar) fechar.addEventListener('click', function () { mostrar(false); abrir.focus(); });
        document.addEventListener('keydown', function (e) {
            if (e.key === 'Escape' && !painel.hidden) { mostrar(false); abrir.focus(); }
        });
    }
})();