"""Orquestra o dia de prospecção: descobrir → auditar → pesquisar → diagnosticar → salvar."""

from __future__ import annotations

import logging
import random
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from datetime import date, datetime
from pathlib import Path

import anthropic

from . import prompts
from .auditoria_site import AuditoriaSite, auditar_site, dominio
from .claude import ClienteClaude
from .config import Config
from .historico import Historico, slug, chaves
from .modelos import AnaliseLead, Candidato, ListaCandidatos
from .relatorio import Falha, LeadAnalisado, salvar_arquivos

log = logging.getLogger(__name__)

# Erros que não adianta tentar de novo com outro lead (chave errada, sem crédito...).
ERROS_FATAIS = (anthropic.AuthenticationError, anthropic.PermissionDeniedError)


@dataclass
class ResultadoDoDia:
    pasta: Path
    leads: list[LeadAnalisado]
    falhas: list[Falha]
    avisos: list[str] = field(default_factory=list)


def segmentos_do_dia(cfg: Config, dia: date) -> list[tuple[str, str]]:
    """Rodízio determinístico de combinações nicho x cidade (muda a cada dia)."""
    combos = [(n, c) for n in cfg.prospeccao.nichos for c in cfg.prospeccao.cidades]
    random.Random(2026).shuffle(combos)  # ordem fixa, mas misturada
    k = min(cfg.prospeccao.segmentos_por_dia, len(combos))
    inicio = (dia.toordinal() * k) % len(combos)
    return [combos[(inicio + i) % len(combos)] for i in range(k)]


def dividir(total: int, partes: int) -> list[int]:
    base, resto = divmod(total, partes)
    return [base + (1 if i < resto else 0) for i in range(partes)]


def descobrir(
    cliente: ClienteClaude,
    cfg: Config,
    nicho: str,
    cidade: str,
    quantidade: int,
    historico: Historico,
    ja_escolhidos: list[Candidato],
) -> list[Candidato]:
    if quantidade <= 0:
        return []
    pedir = quantidade + max(2, quantidade // 2)  # margem para descartar repetidos
    excluir = historico.nomes_recentes(cidade) + [c.nome for c in ja_escolhidos]
    log.info("Descobrindo %s empresas: %s em %s", pedir, nicho, cidade)

    pesquisa = cliente.pesquisar(
        prompts.sistema_descoberta(cfg),
        prompts.pedido_descoberta(nicho, cidade, pedir, excluir),
        esforco=cfg.modelo.esforco_descoberta,
        max_buscas=cfg.modelo.max_buscas_descoberta,
        max_leituras=cfg.modelo.max_buscas_descoberta,
    )
    lista = cliente.estruturar(
        prompts.sistema_estruturar_descoberta(),
        f"Nicho: {nicho}\nCidade: {cidade}\n\nAnotações da pesquisa:\n{pesquisa.texto}",
        ListaCandidatos,
        esforco="low",
    )

    chaves_hoje = {k for c in ja_escolhidos for k in chaves(c.nome, c.cidade, c.site, c.instagram)}
    escolhidos: list[Candidato] = []
    for c in lista.candidatos:
        if not c.nome.strip():
            continue
        c = c.model_copy(update={"nicho": c.nicho or nicho, "cidade": c.cidade or cidade})
        minhas_chaves = set(chaves(c.nome, c.cidade, c.site, c.instagram))
        if minhas_chaves & chaves_hoje or historico.ja_prospectado(c.nome, c.cidade, c.site, c.instagram):
            log.info("  ignorando (já prospectada): %s", c.nome)
            continue
        chaves_hoje |= minhas_chaves
        escolhidos.append(c)
        if len(escolhidos) == quantidade:
            break
    log.info("  %s empresas selecionadas em %s", len(escolhidos), cidade)
    return escolhidos


def _completar_contatos(analise: AnaliseLead, candidato: Candidato, auditoria: AuditoriaSite) -> AnaliseLead:
    """Preenche contatos vazios com o que foi medido por código (site/auditoria)."""
    c = analise.contatos
    redes = auditoria.redes_sociais
    atualizacao = {
        "site": c.site or auditoria.url_final or candidato.site,
        "instagram": c.instagram or candidato.instagram or redes.get("instagram", ""),
        "facebook": c.facebook or redes.get("facebook", ""),
        "linkedin": c.linkedin or redes.get("linkedin", ""),
        "tiktok": c.tiktok or redes.get("tiktok", ""),
        "youtube": c.youtube or redes.get("youtube", ""),
        "email": c.email or (auditoria.emails[0] if auditoria.emails else ""),
        "telefone": c.telefone or (auditoria.telefones[0] if auditoria.telefones else ""),
        "whatsapp": c.whatsapp or (auditoria.whatsapps[0] if auditoria.whatsapps else ""),
    }
    return analise.model_copy(update={"contatos": c.model_copy(update=atualizacao)})


def analisar_candidato(cliente: ClienteClaude, cfg: Config, candidato: Candidato) -> LeadAnalisado:
    log.info("Analisando: %s (%s)", candidato.nome, candidato.cidade)
    auditoria = auditar_site(candidato.site)
    if not candidato.instagram and auditoria.redes_sociais.get("instagram"):
        candidato = candidato.model_copy(update={"instagram": auditoria.redes_sociais["instagram"]})
    resumo = auditoria.resumo()

    pesquisa = cliente.pesquisar(
        prompts.sistema_pesquisa(cfg),
        prompts.pedido_pesquisa(candidato, resumo),
        esforco=cfg.modelo.esforco_pesquisa,
        max_buscas=cfg.modelo.max_buscas_por_lead,
        max_leituras=cfg.modelo.max_leituras_por_lead,
    )
    analise = cliente.estruturar(
        prompts.sistema_analise(cfg),
        prompts.pedido_analise(candidato, resumo, pesquisa.texto, pesquisa.fontes),
        AnaliseLead,
        esforco=cfg.modelo.esforco_analise,
    )
    if not analise.fontes:
        analise = analise.model_copy(update={"fontes": pesquisa.fontes[:20]})

    # Se a pesquisa achou um site que a descoberta não tinha, audita agora para o relatório.
    site_encontrado = analise.contatos.site
    if not auditoria.url_informada and site_encontrado and dominio(site_encontrado):
        auditoria = auditar_site(site_encontrado)

    analise = _completar_contatos(analise, candidato, auditoria)
    log.info("  ✔ %s: score %s (%s)", analise.empresa, analise.score_oportunidade, analise.prioridade)
    return LeadAnalisado(candidato=candidato, auditoria=auditoria, analise=analise)


def _analisar_varios(cliente: ClienteClaude, cfg: Config, candidatos: list[Candidato]) -> tuple[list[LeadAnalisado], list[Falha]]:
    leads: list[LeadAnalisado] = []
    falhas: list[Falha] = []
    with ThreadPoolExecutor(max_workers=cfg.modelo.paralelismo) as pool:
        futuros = {pool.submit(analisar_candidato, cliente, cfg, c): c for c in candidatos}
        for futuro in as_completed(futuros):
            candidato = futuros[futuro]
            try:
                leads.append(futuro.result())
            except ERROS_FATAIS:
                raise
            except Exception as e:  # um lead com problema não derruba o dia inteiro
                log.exception("  ✘ falha ao analisar %s", candidato.nome)
                falhas.append(Falha(candidato=candidato, erro=f"{type(e).__name__}: {e}"))
    return leads, falhas


def _rodape(cfg: Config, cliente: ClienteClaude, avisos: list[str]) -> str:
    u = cliente.uso
    custo = u.custo_estimado(cliente.modelo)
    texto_custo = f" · custo estimado ≈ US$ {custo:.2f}" if custo is not None else ""
    def milhar(n: int) -> str:
        return f"{n:,}".replace(",", ".")

    linhas = [
        f"_Gerado automaticamente pelo agente de prospecção da {cfg.agencia.nome} em "
        f"{datetime.now():%d/%m/%Y %H:%M} · modelo {cliente.modelo} · {u.chamadas} chamadas · "
        f"{u.buscas_web} buscas web · {milhar(u.tokens_entrada + u.tokens_cache_leitura)} tokens de entrada / "
        f"{milhar(u.tokens_saida)} de saída{texto_custo}._"
    ]
    linhas += [f"\n⚠️ {a}" for a in avisos]
    return "\n".join(linhas)


def _registrar(historico: Historico, leads: list[LeadAnalisado], dia: date) -> None:
    for lead in leads:
        c, contatos = lead.candidato, lead.analise.contatos
        historico.registrar(c.nome, c.cidade, contatos.site or c.site, contatos.instagram or c.instagram, hoje=dia)
    historico.salvar()


def executar_dia(
    cfg: Config,
    cliente: ClienteClaude,
    dia: date,
    quantidade: int | None = None,
    segmentos: list[tuple[str, str]] | None = None,
) -> ResultadoDoDia:
    historico = Historico(cfg.arquivo_historico, cfg.saida.dias_para_reprospectar)
    segmentos = segmentos or segmentos_do_dia(cfg, dia)
    total = quantidade or cfg.prospeccao.leads_por_dia
    avisos: list[str] = []

    candidatos: list[Candidato] = []
    for (nicho, cidade), cota in zip(segmentos, dividir(total, len(segmentos))):
        try:
            candidatos += descobrir(cliente, cfg, nicho, cidade, cota, historico, candidatos)
        except ERROS_FATAIS:
            raise
        except Exception as e:
            log.exception("Falha na descoberta de %s em %s", nicho, cidade)
            avisos.append(f"Falha ao buscar {nicho} em {cidade}: {type(e).__name__}: {e}")

    if not candidatos:
        avisos.append("Nenhuma empresa nova encontrada hoje. Considere adicionar nichos/cidades no config.yaml.")

    leads, falhas = _analisar_varios(cliente, cfg, candidatos)
    _registrar(historico, leads, dia)
    pasta = salvar_arquivos(cfg.pasta_leads, dia, segmentos, leads, falhas, _rodape(cfg, cliente, avisos))
    return ResultadoDoDia(pasta=pasta, leads=leads, falhas=falhas, avisos=avisos)


def analisar_empresa(
    cfg: Config,
    cliente: ClienteClaude,
    dia: date,
    nome: str,
    cidade: str,
    nicho: str = "",
    site: str = "",
    instagram: str = "",
) -> ResultadoDoDia:
    """Pré-análise de uma empresa específica (ex.: indicação ou lead que chegou)."""
    candidato = Candidato(
        nome=nome, nicho=nicho or "não informado", cidade=cidade, site=site, instagram=instagram,
        motivo="Empresa indicada manualmente para pré-análise.",
    )
    leads, falhas = _analisar_varios(cliente, cfg, [candidato])
    _registrar(Historico(cfg.arquivo_historico, cfg.saida.dias_para_reprospectar), leads, dia)
    pasta = salvar_arquivos(
        cfg.pasta_leads, dia, [(candidato.nicho, cidade)], leads, falhas, _rodape(cfg, cliente, []),
        nome_pasta=f"{dia.isoformat()}-{slug(nome)}",
    )
    return ResultadoDoDia(pasta=pasta, leads=leads, falhas=falhas)
