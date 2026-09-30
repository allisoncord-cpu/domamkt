"""Geração dos arquivos do dia: relatório em Markdown, planilha CSV e JSON."""

from __future__ import annotations

import csv
import json
import re
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from urllib.parse import quote

from .auditoria_site import AuditoriaSite
from .modelos import AnaliseLead, Candidato

EMOJI_PRIORIDADE = {"alta": "🔥", "média": "🟡", "baixa": "⚪"}


@dataclass
class LeadAnalisado:
    candidato: Candidato
    auditoria: AuditoriaSite
    analise: AnaliseLead


@dataclass
class Falha:
    candidato: Candidato
    erro: str


def _celula(texto) -> str:
    return re.sub(r"\s+", " ", str(texto or "")).replace("|", "\\|").strip()


def _citacao(texto: str) -> str:
    # Dois espaços no fim da linha mantêm as quebras de linha das mensagens no Markdown.
    return "\n".join(f"> {linha.rstrip()}  " if linha.strip() else ">" for linha in (texto or "").strip().splitlines())


def numero_whatsapp(valor: str) -> str:
    """Normaliza para o formato internacional usado pelo wa.me (ex.: 5511999998888)."""
    digitos = re.sub(r"\D", "", valor or "")
    if digitos.startswith("0"):
        digitos = digitos.lstrip("0")
    if len(digitos) in (10, 11):
        digitos = "55" + digitos
    return digitos if len(digitos) in (12, 13) and digitos.startswith("55") else ""


def link_whatsapp(analise: AnaliseLead) -> str:
    numero = numero_whatsapp(analise.contatos.whatsapp) or numero_whatsapp(analise.contatos.telefone)
    if not numero:
        return ""
    return f"https://wa.me/{numero}?text={quote(analise.mensagem_whatsapp)}"


def link_email(analise: AnaliseLead) -> str:
    email = analise.contatos.email.strip()
    if "@" not in email:
        return ""
    return f"mailto:{email}?subject={quote(analise.email_assunto)}&body={quote(analise.email_corpo)}"


def ordenar(leads: list[LeadAnalisado]) -> list[LeadAnalisado]:
    return sorted(leads, key=lambda l: l.analise.score_oportunidade, reverse=True)


def _contato_principal(a: AnaliseLead) -> str:
    c = a.contatos
    for rotulo, valor in (("WhatsApp", c.whatsapp), ("Tel", c.telefone), ("E-mail", c.email), ("Instagram", c.instagram)):
        if valor.strip():
            return f"{rotulo}: {valor.strip()}"
    return "—"


def _secao_lead(i: int, lead: LeadAnalisado) -> str:
    a, c, aud = lead.analise, lead.analise.contatos, lead.auditoria
    emoji = EMOJI_PRIORIDADE.get(a.prioridade, "")
    partes = [
        f'<a id="lead-{i}"></a>',
        "",
        f"## {i}. {a.empresa} — {a.score_oportunidade}/100 {emoji} prioridade {a.prioridade}",
        f"**{a.segmento}** · {a.cidade} · porte: {a.porte_estimado} · confiança dos dados: {a.confianca_dos_dados}",
        "",
        _citacao(a.resumo_empresa),
        "",
        "### Contatos",
    ]
    contatos = [
        ("Site", c.site), ("Instagram", c.instagram), ("Facebook", c.facebook), ("LinkedIn", c.linkedin),
        ("TikTok", c.tiktok), ("YouTube", c.youtube), ("Google Maps", c.google_meu_negocio),
        ("WhatsApp", c.whatsapp), ("Telefone", c.telefone), ("E-mail", c.email), ("Endereço", c.endereco),
        ("Decisor", c.decisor),
    ]
    partes += [f"- **{rotulo}:** {valor}" for rotulo, valor in contatos if valor.strip()]
    if not any(v.strip() for _, v in contatos):
        partes.append("- Nenhum contato público encontrado.")

    partes += ["", "### Diagnóstico por área", "", "| Área | Nota | Situação atual | O que melhorar |", "|---|:---:|---|---|"]
    for av in a.avaliacoes:
        melhorias = "<br>".join(f"• {_celula(m)}" for m in av.o_que_melhorar) or "—"
        partes.append(f"| {av.area} | {av.nota}/10 | {_celula(av.situacao_atual)} | {melhorias} |")

    def lista(titulo: str, itens: list[str], numerada: bool = False) -> None:
        if itens:
            partes.extend(["", f"### {titulo}"])
            partes.extend(f"{n}. {x}" if numerada else f"- {x}" for n, x in enumerate(itens, 1))

    lista("Principais oportunidades", a.principais_oportunidades, numerada=True)
    lista("Serviços da agência recomendados", a.servicos_recomendados)
    lista("Pontos fortes", a.pontos_fortes)
    lista("Sinais de que pode investir", a.sinais_de_investimento)
    lista("Concorrentes de referência", a.concorrentes_referencia)

    partes += ["", "### Auditoria técnica do site"]
    if aud.acessivel:
        if aud.pagespeed_mobile:
            partes.append("- PageSpeed mobile: " + ", ".join(f"{k} {v}/100" for k, v in aud.pagespeed_mobile.items()))
        partes.extend(f"- ⚠️ {p}" for p in aud.problemas)
        if not aud.problemas:
            partes.append("- Nenhum problema técnico básico encontrado.")
    else:
        partes.append(f"- {aud.resumo()}")

    partes += ["", "### Abordagem", f"**Gancho:** {a.gancho_abordagem}", "", "**WhatsApp**", "", _citacao(a.mensagem_whatsapp)]
    if wa := link_whatsapp(a):
        partes += ["", f"[Abrir no WhatsApp com a mensagem pronta]({wa})"]
    partes += ["", f"**E-mail** — assunto: *{a.email_assunto}*", "", _citacao(a.email_corpo)]
    if mail := link_email(a):
        partes += ["", f"[Abrir e-mail pronto]({mail})"]
    partes += ["", "**Direct do Instagram**", "", _citacao(a.mensagem_direct_instagram)]

    if a.observacoes.strip():
        partes += ["", f"**Observações:** {a.observacoes}"]
    if a.fontes:
        partes += ["", "<details><summary>Fontes consultadas</summary>", ""]
        partes += [f"- {f}" for f in a.fontes]
        partes += ["", "</details>"]
    return "\n".join(partes)


def gerar_markdown(dia: date, segmentos: list[tuple[str, str]], leads: list[LeadAnalisado], falhas: list[Falha], rodape: str) -> str:
    leads = ordenar(leads)
    partes = [
        f"# Leads do dia — {dia:%d/%m/%Y}",
        "",
        "**Segmentos pesquisados:** " + "; ".join(f"{n} em {c}" for n, c in segmentos),
        "",
        f"**{len(leads)} leads analisados.** Revise antes de enviar: confira os contatos e ajuste as mensagens ao seu jeito.",
        "",
    ]
    if leads:
        partes += ["| # | Empresa | Segmento | Cidade | Score | Prioridade | Principal oportunidade | Contato |", "|---|---|---|---|:---:|---|---|---|"]
        for i, lead in enumerate(leads, 1):
            a = lead.analise
            oportunidade = a.principais_oportunidades[0] if a.principais_oportunidades else "—"
            partes.append(
                f"| {i} | [{_celula(a.empresa)}](#lead-{i}) | {_celula(a.segmento)} | {_celula(a.cidade)} | "
                f"{a.score_oportunidade} | {EMOJI_PRIORIDADE.get(a.prioridade, '')} {a.prioridade} | {_celula(oportunidade)} | {_celula(_contato_principal(a))} |"
            )
        partes.append("")
        for i, lead in enumerate(leads, 1):
            partes += ["---", "", _secao_lead(i, lead), ""]
    if falhas:
        partes += ["---", "", "## Empresas que não puderam ser analisadas", ""]
        partes += [f"- **{f.candidato.nome}** ({f.candidato.cidade}): {f.erro}" for f in falhas]
        partes.append("")
    partes += ["---", "", rodape, ""]
    return "\n".join(partes)


COLUNAS_CSV = [
    "data", "prioridade", "score", "empresa", "segmento", "cidade", "porte", "site", "instagram", "facebook",
    "linkedin", "tiktok", "google_maps", "whatsapp", "telefone", "email", "endereco", "decisor",
    "principais_oportunidades", "servicos_recomendados", "gancho", "mensagem_whatsapp", "link_whatsapp",
    "email_assunto", "email_corpo", "mensagem_direct", "problemas_site", "confianca", "status",
]


def linhas_csv(dia: date, leads: list[LeadAnalisado]) -> list[dict]:
    linhas = []
    for lead in ordenar(leads):
        a, c = lead.analise, lead.analise.contatos
        linhas.append({
            "data": dia.isoformat(), "prioridade": a.prioridade, "score": a.score_oportunidade, "empresa": a.empresa,
            "segmento": a.segmento, "cidade": a.cidade, "porte": a.porte_estimado, "site": c.site,
            "instagram": c.instagram, "facebook": c.facebook, "linkedin": c.linkedin, "tiktok": c.tiktok,
            "google_maps": c.google_meu_negocio, "whatsapp": c.whatsapp, "telefone": c.telefone, "email": c.email,
            "endereco": c.endereco, "decisor": c.decisor,
            "principais_oportunidades": " | ".join(a.principais_oportunidades),
            "servicos_recomendados": " | ".join(a.servicos_recomendados), "gancho": a.gancho_abordagem,
            "mensagem_whatsapp": a.mensagem_whatsapp, "link_whatsapp": link_whatsapp(a),
            "email_assunto": a.email_assunto, "email_corpo": a.email_corpo,
            "mensagem_direct": a.mensagem_direct_instagram, "problemas_site": " | ".join(lead.auditoria.problemas),
            "confianca": a.confianca_dos_dados, "status": "a contatar",
        })
    return linhas


def salvar_arquivos(
    pasta: Path,
    dia: date,
    segmentos: list[tuple[str, str]],
    leads: list[LeadAnalisado],
    falhas: list[Falha],
    rodape: str,
    nome_pasta: str | None = None,
) -> Path:
    destino = pasta / (nome_pasta or dia.isoformat())
    destino.mkdir(parents=True, exist_ok=True)

    (destino / "relatorio.md").write_text(gerar_markdown(dia, segmentos, leads, falhas, rodape), encoding="utf-8")

    # utf-8-sig + ";" para abrir certinho no Excel em português e no Google Planilhas.
    with open(destino / "leads.csv", "w", newline="", encoding="utf-8-sig") as f:
        escritor = csv.DictWriter(f, fieldnames=COLUNAS_CSV, delimiter=";")
        escritor.writeheader()
        escritor.writerows(linhas_csv(dia, leads))

    dados = {
        "data": dia.isoformat(),
        "segmentos": [{"nicho": n, "cidade": c} for n, c in segmentos],
        "leads": [
            {"analise": l.analise.model_dump(), "auditoria_site": l.auditoria.para_dict(), "candidato": l.candidato.model_dump()}
            for l in ordenar(leads)
        ],
        "falhas": [{"empresa": f.candidato.nome, "cidade": f.candidato.cidade, "erro": f.erro} for f in falhas],
    }
    (destino / "leads.json").write_text(json.dumps(dados, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return destino
