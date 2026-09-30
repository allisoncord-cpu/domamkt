import threading
from datetime import date
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import pytest

from prospector.auditoria_site import AuditoriaSite, analisar_html, auditar_site, dominio, normalizar_url

FIXTURES = Path(__file__).parent / "fixtures"


def test_analisar_html_detecta_sinais_de_marketing():
    html = (FIXTURES / "site_exemplo.html").read_text(encoding="utf-8")
    a = analisar_html(AuditoriaSite(url_informada="https://sorrisofeliz.com.br", https=True), html)

    assert a.titulo == "Clínica Sorriso Feliz | Dentista em Campinas"
    assert a.meta_descricao == ""
    assert a.plataforma == "WordPress"
    assert a.rastreamento["google_analytics"] is True
    assert a.rastreamento["meta_pixel"] is False
    assert a.tem_link_whatsapp and a.whatsapps == ["5519999998888"]
    assert a.emails == ["contato@sorrisofeliz.com.br"]  # ignora logo@2x.png
    assert any("3222" in t for t in a.telefones)
    assert a.redes_sociais["instagram"] == "https://www.instagram.com/sorrisofeliz.campinas"
    assert a.redes_sociais["facebook"] == "https://www.facebook.com/sorrisofelizcampinas"
    assert a.tem_formulario and a.qtd_h1 == 0 and a.ano_copyright == 2019

    problemas = " | ".join(a.problemas)
    assert "meta description" in problemas
    assert "Pixel da Meta" in problemas
    assert "meta viewport" in problemas
    assert "2019" in problemas
    assert "Google Analytics" not in problemas  # tem GA, não deve reclamar


@pytest.fixture
def servidor_local():
    handler = partial(SimpleHTTPRequestHandler, directory=str(FIXTURES))
    handler.log_message = lambda *a, **k: None
    servidor = ThreadingHTTPServer(("127.0.0.1", 0), handler)
    thread = threading.Thread(target=servidor.serve_forever, daemon=True)
    thread.start()
    yield f"http://127.0.0.1:{servidor.server_address[1]}"
    servidor.shutdown()


def test_auditar_site_de_verdade_via_http(servidor_local, monkeypatch):
    monkeypatch.setenv("NO_PROXY", "127.0.0.1,localhost")
    a = auditar_site(f"{servidor_local}/site_exemplo.html", pagespeed_key="")
    assert a.acessivel and a.status_http == 200
    assert a.https is False
    assert any("HTTPS" in p for p in a.problemas)
    assert "WordPress" in a.resumo()


def test_site_inacessivel(servidor_local, monkeypatch):
    monkeypatch.setenv("NO_PROXY", "127.0.0.1,localhost")
    a = auditar_site(f"{servidor_local}/nao-existe.html", pagespeed_key="")
    assert not a.acessivel and a.erro == "HTTP 404"
    assert "NÃO pôde ser acessado" in a.resumo()


def test_sem_site():
    a = auditar_site("")
    assert not a.acessivel
    assert "não informou site" in a.resumo()


def test_normalizacao_de_url_e_dominio():
    assert normalizar_url("clinica.com.br") == "https://clinica.com.br"
    assert dominio("http://www.Clinica.com.br/contato") == "clinica.com.br"
    assert dominio("") == ""
    # textos que a IA pode devolver no lugar de um site não viram domínio
    for lixo in ("não encontrado", "nenhum", "N/A", "-", "sem site"):
        assert normalizar_url(lixo) == "" and dominio(lixo) == ""
    assert auditar_site("não encontrado").url_informada == ""


def test_copyright_futuro_e_ignorado():
    html = f"<footer>© {date.today().year + 5}</footer>"
    a = analisar_html(AuditoriaSite(url_informada="x", https=True), html)
    assert a.ano_copyright is None
