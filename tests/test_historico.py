from datetime import date

from prospector.historico import Historico, chaves, handle_instagram


def test_chaves_identificam_a_empresa_por_site_instagram_e_nome():
    assert chaves("Clínica Bella", "São Paulo - SP", "https://www.bella.com.br", "@Bella.Clinica") == [
        "site:bella.com.br",
        "ig:bella.clinica",
        "nome:clinica-bella|sao-paulo",
    ]
    assert chaves("Loja X", "Embu-Guaçu - SP") == ["nome:loja-x|embu-guacu"]


def test_handle_instagram():
    assert handle_instagram("https://www.instagram.com/padaria.boa/") == "padaria.boa"
    assert handle_instagram("@padaria.boa") == "padaria.boa"
    assert handle_instagram("não encontrado") == ""
    assert handle_instagram("nenhum") == ""


def test_placeholders_nao_juntam_empresas_diferentes():
    assert chaves("Loja A", "Curitiba - PR", "não encontrado", "nenhum") == ["nome:loja-a|curitiba"]


def test_historico_evita_repeticao_e_expira(tmp_path):
    caminho = tmp_path / "historico.json"
    h = Historico(caminho, dias_para_reprospectar=30)
    h.registrar("Clínica Bella", "Curitiba - PR", "bella.com.br", "", hoje=date(2026, 1, 1))
    h.salvar()

    h2 = Historico(caminho, dias_para_reprospectar=30)
    # mesma empresa achada por outro caminho (só o site, com www)
    assert h2.ja_prospectado("Bella Estética", "Curitiba - PR", "https://www.bella.com.br", hoje=date(2026, 1, 15))
    # mesmo nome e cidade, sem site
    assert h2.ja_prospectado("Clinica Bella", "Curitiba - PR", hoje=date(2026, 1, 15))
    # outra cidade, outro site: é outra empresa
    assert not h2.ja_prospectado("Clínica Bella", "Londrina - PR", hoje=date(2026, 1, 15))
    # depois da janela pode voltar a ser prospectada
    assert not h2.ja_prospectado("Clínica Bella", "Curitiba - PR", "bella.com.br", hoje=date(2026, 3, 1))

    assert h2.nomes_recentes("Curitiba - PR", hoje=date(2026, 1, 15)) == ["Clínica Bella"]
    assert h2.nomes_recentes("Londrina - PR", hoje=date(2026, 1, 15)) == []
