"""Roda o dia inteiro de prospecção com um Claude simulado e confere os arquivos gerados."""

import csv
import json
import shutil
from datetime import date
from pathlib import Path

from prospector.claude import ResultadoPesquisa, Uso
from prospector.config import carregar_config
from prospector.modelos import AnaliseLead, AvaliacaoArea, Candidato, Contatos, ListaCandidatos
from prospector.pipeline import analisar_empresa, dividir, executar_dia, segmentos_do_dia

RAIZ = Path(__file__).resolve().parents[1]


def _analise(nome: str, cidade: str, score: int) -> AnaliseLead:
    return AnaliseLead(
        empresa=nome, segmento="clínicas de estética", cidade=cidade,
        resumo_empresa="Clínica de estética com 2 unidades.", porte_estimado="pequena",
        contatos=Contatos(site="", instagram=f"https://instagram.com/{nome.lower().replace(' ', '')}", facebook="",
                          linkedin="", tiktok="", youtube="", google_meu_negocio="", whatsapp="(41) 99999-8888",
                          telefone="", email="", endereco="Rua A, 10", decisor=""),
        avaliacoes=[AvaliacaoArea(area="Instagram", nota=3, situacao_atual="Último post há 4 meses | sem reels",
                                  o_que_melhorar=["Postar 3x por semana", "Usar reels"], evidencias=["instagram"])],
        pontos_fortes=["Boa localização"], principais_oportunidades=["Reativar o Instagram", "Anunciar no Meta Ads"],
        servicos_recomendados=["Gestão de redes sociais"], sinais_de_investimento=["2 unidades"],
        concorrentes_referencia=["Clínica Y"], score_oportunidade=score,
        prioridade="alta" if score >= 70 else "média", gancho_abordagem="Instagram parado há 4 meses",
        mensagem_whatsapp="Oi! Vi o trabalho de vocês...", email_assunto="Ideia para o Instagram",
        email_corpo="Olá...\nSe não fizer sentido, é só me avisar.", mensagem_direct_instagram="Oi!",
        confianca_dos_dados="média", observacoes="", fontes=["https://exemplo.com"],
    )


class ClaudeFalso:
    """Imita o ClienteClaude: descoberta devolve empresas fixas; análise, um diagnóstico."""

    def __init__(self):
        self.modelo = "claude-opus-5-5"
        self.uso = Uso()
        self.pedidos_descoberta = []

    def pesquisar(self, sistema, pedido, esforco, max_buscas, max_leituras):
        if pedido.startswith("Encontre"):
            self.pedidos_descoberta.append(pedido)
        return ResultadoPesquisa(texto="anotações", fontes=["https://exemplo.com"])

    def estruturar(self, sistema, pedido, formato, esforco):
        cidade = pedido.split("Cidade: ")[1].split("\n")[0].split(" |")[0]
        if formato is ListaCandidatos:
            nomes = ["Clínica Alfa", "Clínica Beta", "Clínica Gama", "Clínica Delta", "Clínica Épsilon"]
            return ListaCandidatos(candidatos=[
                Candidato(nome=n, nicho="clínicas de estética", cidade=cidade, site="", instagram="", motivo="Instagram parado")
                for n in nomes
            ])
        nome = pedido.split("Empresa: ")[1].split(" |")[0]
        return _analise(nome, cidade, score=90 if "Beta" in nome else 60)


def _config(tmp_path: Path):
    shutil.copy(RAIZ / "config.yaml", tmp_path / "config.yaml")
    cfg = carregar_config(tmp_path / "config.yaml")
    cfg.prospeccao.leads_por_dia = 4
    return cfg


def test_rodizio_de_segmentos_muda_por_dia_e_cobre_tudo():
    cfg = carregar_config(RAIZ / "config.yaml")
    total = len(cfg.prospeccao.nichos) * len(cfg.prospeccao.cidades)
    vistos = set()
    for d in range(total):
        segs = segmentos_do_dia(cfg, date(2026, 1, 1).fromordinal(date(2026, 1, 1).toordinal() + d))
        assert len(segs) == cfg.prospeccao.segmentos_por_dia
        vistos.update(segs)
    assert len(vistos) == total
    assert dividir(10, 3) == [4, 3, 3]


def test_dia_completo_gera_relatorio_csv_json_e_nao_repete(tmp_path):
    cfg = _config(tmp_path)
    claude = ClaudeFalso()
    dia = date(2026, 9, 30)
    segmentos = [("clínicas de estética", "Curitiba - PR")]

    r = executar_dia(cfg, claude, dia, segmentos=segmentos)

    assert len(r.leads) == 4 and not r.falhas
    relatorio = (r.pasta / "relatorio.md").read_text(encoding="utf-8")
    assert "# Leads do dia — 30/09/2026" in relatorio
    # ordenado por score: Beta (90) primeiro
    assert relatorio.index("## 1. Clínica Beta") < relatorio.index("## 2. ")
    assert "https://wa.me/5541999998888?text=" in relatorio
    assert "Último post há 4 meses \\| sem reels" in relatorio  # pipe escapado na tabela

    with open(r.pasta / "leads.csv", encoding="utf-8-sig") as f:
        linhas = list(csv.DictReader(f, delimiter=";"))
    assert [l["empresa"] for l in linhas][0] == "Clínica Beta"
    assert linhas[0]["status"] == "a contatar"

    dados = json.loads((r.pasta / "leads.json").read_text(encoding="utf-8"))
    assert len(dados["leads"]) == 4

    # Segunda rodada no dia seguinte: as 4 já prospectadas são excluídas.
    claude2 = ClaudeFalso()
    r2 = executar_dia(cfg, claude2, date(2026, 10, 1), segmentos=segmentos)
    assert [l.candidato.nome for l in r2.leads] == ["Clínica Épsilon"]
    assert "Clínica Alfa" in claude2.pedidos_descoberta[0]  # lista de exclusão enviada ao agente


def test_falha_em_um_lead_nao_derruba_o_dia(tmp_path):
    cfg = _config(tmp_path)

    class ClaudeComFalha(ClaudeFalso):
        def estruturar(self, sistema, pedido, formato, esforco):
            if "Empresa: Clínica Gama" in pedido:
                raise RuntimeError("erro simulado")
            return super().estruturar(sistema, pedido, formato, esforco)

    r = executar_dia(cfg, ClaudeComFalha(), date(2026, 9, 30), segmentos=[("clínicas de estética", "Curitiba - PR")])
    assert len(r.leads) == 3
    assert [f.candidato.nome for f in r.falhas] == ["Clínica Gama"]
    assert "não puderam ser analisadas" in (r.pasta / "relatorio.md").read_text(encoding="utf-8")


def test_analisar_empresa_avulsa(tmp_path):
    cfg = _config(tmp_path)
    r = analisar_empresa(cfg, ClaudeFalso(), date(2026, 9, 30), "Clínica Bella", "Curitiba - PR")
    assert r.pasta.name == "2026-09-30-clinica-bella"
    assert len(r.leads) == 1
