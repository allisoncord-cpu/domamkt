"""Auditoria técnica rápida do site do lead (sem IA, só código).

Dá ao agente fatos objetivos para o diagnóstico: HTTPS, velocidade, SEO básico,
versão mobile, pixels de anúncio, botão de WhatsApp, contatos e redes sociais
linkadas no site. Opcionalmente consulta o Google PageSpeed (nota de 0 a 100).
"""

from __future__ import annotations

import os
import re
import time
from dataclasses import asdict, dataclass, field
from datetime import date
from urllib.parse import urlparse

import requests

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/126.0 Safari/537.36"
)
PAGESPEED_URL = "https://www.googleapis.com/pagespeedonline/v5/runPagespeed"

RASTREADORES = {
    "meta_pixel": [r"connect\.facebook\.net/[^\"']*/fbevents\.js", r"fbq\(\s*['\"]init"],
    "google_analytics": [r"googletagmanager\.com/gtag/js\?id=G-", r"google-analytics\.com/(analytics|ga)\.js", r"gtag\(\s*['\"]config['\"]\s*,\s*['\"]G-"],
    "google_tag_manager": [r"googletagmanager\.com/gtm\.js", r"GTM-[A-Z0-9]{4,}"],
    "google_ads": [r"gtag\(\s*['\"]config['\"]\s*,\s*['\"]AW-", r"googleadservices\.com", r"googletagmanager\.com/gtag/js\?id=AW-"],
    "tiktok_pixel": [r"analytics\.tiktok\.com"],
    "hotjar_ou_clarity": [r"static\.hotjar\.com", r"clarity\.ms"],
    "rd_station": [r"d335luupugsy2\.cloudfront\.net", r"rdstation"],
}

PLATAFORMAS = {
    "WordPress": [r"wp-content/", r"wp-includes/"],
    "Wix": [r"static\.wixstatic\.com", r"wix\.com"],
    "Shopify": [r"cdn\.shopify\.com"],
    "Nuvemshop": [r"nuvemshop", r"tiendanube"],
    "Squarespace": [r"squarespace\.com"],
    "Webflow": [r"webflow\.com"],
    "Loja Integrada": [r"lojaintegrada"],
    "VTEX": [r"vtex"],
}

REDES = {
    "instagram": re.compile(r"https?://(?:www\.)?instagram\.com/(?!p/|reel/|reels/|explore/|stories/|accounts/)([A-Za-z0-9_.]{2,30})/?", re.I),
    "facebook": re.compile(r"https?://(?:www\.|m\.|pt-br\.)?facebook\.com/(?!sharer|share|tr\?|plugins|dialog|login|events/)([A-Za-z0-9_.\-/]{2,80})", re.I),
    "linkedin": re.compile(r"https?://(?:[a-z]{2,3}\.)?linkedin\.com/(?:company|in|school)/[A-Za-z0-9_\-%.]+/?", re.I),
    "tiktok": re.compile(r"https?://(?:www\.)?tiktok\.com/@[A-Za-z0-9_.]+", re.I),
    "youtube": re.compile(r"https?://(?:www\.)?youtube\.com/(?:@|channel/|c/|user/)[A-Za-z0-9_\-.]+", re.I),
}

RE_EMAIL = re.compile(r"[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}")
RE_TEL_HREF = re.compile(r"href=[\"']tel:([+\d\s().\-]{8,20})[\"']", re.I)
RE_WHATSAPP = re.compile(r"https?://(?:api\.whatsapp\.com/send\?phone=|wa\.me/|web\.whatsapp\.com/send\?phone=)(\+?\d{10,15})", re.I)
RE_TEL_TEXTO = re.compile(r"\(?\b\d{2}\)?\s?9?\d{4}[\s\-]\d{4}\b")
RE_COPYRIGHT = re.compile(r"(?:©|&copy;|copyright)\s*(?:\d{4}\s*[-–]\s*)?(\d{4})", re.I)
EMAILS_IGNORADOS = ("example.", "sentry", "wixpress", "@2x", ".png", ".jpg", ".jpeg", ".webp", ".gif", ".svg", "domain.com", "email.com", "seuemail", "seudominio")


@dataclass
class AuditoriaSite:
    url_informada: str
    url_final: str = ""
    acessivel: bool = False
    status_http: int | None = None
    https: bool = False
    certificado_invalido: bool = False
    tempo_resposta_s: float | None = None
    plataforma: str = ""
    titulo: str = ""
    meta_descricao: str = ""
    tem_viewport_mobile: bool = False
    qtd_h1: int = 0
    tem_open_graph: bool = False
    tem_dados_estruturados: bool = False
    rastreamento: dict[str, bool] = field(default_factory=dict)
    tem_link_whatsapp: bool = False
    tem_formulario: bool = False
    tem_blog: bool = False
    ano_copyright: int | None = None
    emails: list[str] = field(default_factory=list)
    telefones: list[str] = field(default_factory=list)
    whatsapps: list[str] = field(default_factory=list)
    redes_sociais: dict[str, str] = field(default_factory=dict)
    pagespeed_mobile: dict[str, int] = field(default_factory=dict)
    problemas: list[str] = field(default_factory=list)
    erro: str = ""

    def para_dict(self) -> dict:
        return asdict(self)

    def resumo(self) -> str:
        """Texto curto e legível para entregar ao agente e ao relatório."""
        if not self.url_informada:
            return "A empresa não informou site (nenhum site encontrado)."
        if not self.acessivel:
            return f"Site {self.url_informada} NÃO pôde ser acessado ({self.erro or 'erro desconhecido'})."
        rastreios = [nome for nome, ativo in self.rastreamento.items() if ativo]
        linhas = [
            f"URL final: {self.url_final} (HTTP {self.status_http}, HTTPS: {'sim' if self.https else 'não'})",
            f"Tempo de resposta: {self.tempo_resposta_s}s | Plataforma: {self.plataforma or 'não identificada'}",
            f"Título: {self.titulo or '(sem título)'}",
            f"Meta description: {self.meta_descricao or '(ausente)'}",
            f"Responsivo (meta viewport): {'sim' if self.tem_viewport_mobile else 'não'} | H1: {self.qtd_h1} | "
            f"Open Graph: {'sim' if self.tem_open_graph else 'não'} | Dados estruturados: {'sim' if self.tem_dados_estruturados else 'não'}",
            f"Rastreamento/pixels: {', '.join(rastreios) if rastreios else 'nenhum detectado'}",
            f"Botão/link de WhatsApp: {'sim' if self.tem_link_whatsapp else 'não'} | Formulário: {'sim' if self.tem_formulario else 'não'} | "
            f"Blog: {'sim' if self.tem_blog else 'não'} | Ano no rodapé: {self.ano_copyright or 'n/d'}",
        ]
        if self.pagespeed_mobile:
            notas = ", ".join(f"{k}: {v}/100" for k, v in self.pagespeed_mobile.items())
            linhas.append(f"Google PageSpeed (mobile): {notas}")
        if self.redes_sociais:
            linhas.append("Redes linkadas no site: " + ", ".join(f"{k}: {v}" for k, v in self.redes_sociais.items()))
        contatos = self.emails + self.telefones + [f"WhatsApp {w}" for w in self.whatsapps]
        if contatos:
            linhas.append("Contatos no site: " + ", ".join(contatos))
        if self.problemas:
            linhas.append("Problemas detectados: " + "; ".join(self.problemas))
        return "\n".join(linhas)


def normalizar_url(url: str) -> str:
    """Devolve a URL com https:// ou '' se não parecer um endereço (ex.: 'não encontrado')."""
    url = (url or "").strip().rstrip(".,;)")
    if not url or re.search(r"\s", url):
        return ""
    if not re.match(r"^https?://", url, re.I):
        url = "https://" + url
    host = urlparse(url).netloc.split(":")[0]
    eh_dominio = re.fullmatch(r"[A-Za-z0-9\-.]+\.[A-Za-z]{2,}", host)
    eh_ip = re.fullmatch(r"\d{1,3}(\.\d{1,3}){3}", host)
    if not (eh_dominio or eh_ip or host == "localhost"):
        return ""
    return url


def _primeiro(padrao: str, html: str) -> str:
    m = re.search(padrao, html, re.I | re.S)
    return re.sub(r"\s+", " ", m.group(1)).strip() if m else ""


def _meta(html: str, nome: str) -> str:
    for padrao in (
        rf"<meta[^>]+(?:name|property)=[\"']{nome}[\"'][^>]*content=[\"']([^\"']*)[\"']",
        rf"<meta[^>]+content=[\"']([^\"']*)[\"'][^>]*(?:name|property)=[\"']{nome}[\"']",
    ):
        valor = _primeiro(padrao, html)
        if valor:
            return valor
    return ""


def _algum(padroes: list[str], html: str) -> bool:
    return any(re.search(p, html, re.I) for p in padroes)


def _unicos(itens, limite: int = 5) -> list[str]:
    vistos: list[str] = []
    for item in itens:
        item = item.strip()
        if item and item not in vistos:
            vistos.append(item)
        if len(vistos) >= limite:
            break
    return vistos


def analisar_html(auditoria: AuditoriaSite, html: str) -> AuditoriaSite:
    """Preenche a auditoria a partir do HTML da página inicial."""
    auditoria.titulo = _primeiro(r"<title[^>]*>(.*?)</title>", html)[:200]
    auditoria.meta_descricao = _meta(html, "description")[:300]
    auditoria.tem_viewport_mobile = bool(re.search(r"<meta[^>]+name=[\"']viewport[\"']", html, re.I))
    auditoria.qtd_h1 = len(re.findall(r"<h1[\s>]", html, re.I))
    auditoria.tem_open_graph = bool(_meta(html, "og:title") or _meta(html, "og:image"))
    auditoria.tem_dados_estruturados = "application/ld+json" in html.lower() or "itemtype=\"http" in html.lower()
    auditoria.rastreamento = {nome: _algum(padroes, html) for nome, padroes in RASTREADORES.items()}
    auditoria.plataforma = next((nome for nome, padroes in PLATAFORMAS.items() if _algum(padroes, html)), "")
    auditoria.tem_formulario = bool(re.search(r"<form[\s>]", html, re.I))
    auditoria.tem_blog = bool(re.search(r"href=[\"'][^\"']*/(blog|noticias|artigos)[/\"']", html, re.I))

    anos = [int(a) for a in RE_COPYRIGHT.findall(html) if 1995 <= int(a) <= date.today().year + 1]
    auditoria.ano_copyright = max(anos) if anos else None

    emails = [e for e in RE_EMAIL.findall(html) if not any(x in e.lower() for x in EMAILS_IGNORADOS)]
    auditoria.emails = _unicos(e.lower() for e in emails)

    whatsapps = RE_WHATSAPP.findall(html)
    auditoria.whatsapps = _unicos(whatsapps, 3)
    minusculo = html.lower()
    auditoria.tem_link_whatsapp = bool(whatsapps) or "wa.me/" in minusculo or "api.whatsapp.com" in minusculo

    texto = re.sub(r"<[^>]+>", " ", re.sub(r"<(script|style)[^>]*>.*?</\1>", " ", html, flags=re.I | re.S))
    telefones = RE_TEL_HREF.findall(html) + RE_TEL_TEXTO.findall(texto)
    auditoria.telefones = _unicos(telefones, 4)

    for rede, regex in REDES.items():
        m = regex.search(html)
        if m:
            auditoria.redes_sociais[rede] = m.group(0).rstrip("/\"'")

    auditoria.problemas = listar_problemas(auditoria)
    return auditoria


def listar_problemas(a: AuditoriaSite) -> list[str]:
    p: list[str] = []
    if a.certificado_invalido:
        p.append("certificado HTTPS inválido (navegador mostra alerta de segurança)")
    elif not a.https:
        p.append("site sem HTTPS (aparece como 'não seguro' no navegador)")
    if a.tempo_resposta_s is not None and a.tempo_resposta_s > 3:
        p.append(f"servidor lento ({a.tempo_resposta_s}s só para responder)")
    if not a.tem_viewport_mobile:
        p.append("sem meta viewport (provavelmente não é adaptado para celular)")
    if not a.meta_descricao:
        p.append("sem meta description (prejudica o SEO e o clique no Google)")
    if not a.titulo:
        p.append("página sem título")
    if a.qtd_h1 == 0:
        p.append("página inicial sem título H1")
    if not a.tem_open_graph:
        p.append("sem Open Graph (links compartilhados no WhatsApp/redes ficam sem imagem)")
    if not a.rastreamento.get("meta_pixel"):
        p.append("sem Pixel da Meta (não dá para fazer remarketing no Instagram/Facebook)")
    if not (a.rastreamento.get("google_analytics") or a.rastreamento.get("google_tag_manager")):
        p.append("sem Google Analytics/Tag Manager (não mede visitas e conversões)")
    if not a.tem_link_whatsapp:
        p.append("sem botão de WhatsApp no site")
    if a.ano_copyright and a.ano_copyright < date.today().year - 1:
        p.append(f"rodapé com ano {a.ano_copyright} (sinal de site desatualizado)")
    perf = a.pagespeed_mobile.get("performance")
    if perf is not None and perf < 50:
        p.append(f"nota de desempenho mobile baixa no Google PageSpeed ({perf}/100)")
    return p


def consultar_pagespeed(url: str, chave: str, timeout: int = 90) -> dict[str, int]:
    params = [("url", url), ("strategy", "mobile"), ("key", chave)]
    params += [("category", c) for c in ("performance", "seo", "accessibility", "best-practices")]
    resp = requests.get(PAGESPEED_URL, params=params, timeout=timeout)
    resp.raise_for_status()
    categorias = resp.json().get("lighthouseResult", {}).get("categories", {})
    return {
        nome.replace("best-practices", "boas_praticas").replace("accessibility", "acessibilidade"): round(dados["score"] * 100)
        for nome, dados in categorias.items()
        if dados.get("score") is not None
    }


def auditar_site(url: str, timeout: int = 20, pagespeed_key: str | None = None) -> AuditoriaSite:
    url = normalizar_url(url)
    auditoria = AuditoriaSite(url_informada=url)
    if not url:
        return auditoria

    inicio = time.monotonic()
    try:
        resp = requests.get(url, timeout=timeout, headers={"User-Agent": USER_AGENT, "Accept-Language": "pt-BR,pt;q=0.9"})
    except requests.exceptions.SSLError:
        # Muitos sites pequenos têm certificado quebrado: tenta via http e registra o problema.
        try:
            resp = requests.get(url.replace("https://", "http://", 1), timeout=timeout, headers={"User-Agent": USER_AGENT})
            auditoria.certificado_invalido = True
        except requests.RequestException as e:
            auditoria.erro = f"certificado inválido e falha no http: {type(e).__name__}"
            return auditoria
    except requests.RequestException as e:
        auditoria.erro = type(e).__name__
        return auditoria

    auditoria.tempo_resposta_s = round(time.monotonic() - inicio, 2)
    auditoria.status_http = resp.status_code
    auditoria.url_final = resp.url
    auditoria.https = urlparse(resp.url).scheme == "https"
    if resp.status_code >= 400:
        auditoria.erro = f"HTTP {resp.status_code}"
        return auditoria

    auditoria.acessivel = True
    if not resp.encoding or resp.encoding.lower() == "iso-8859-1":
        resp.encoding = resp.apparent_encoding
    analisar_html(auditoria, resp.text)

    chave = pagespeed_key if pagespeed_key is not None else os.environ.get("PAGESPEED_API_KEY")
    if chave:
        try:
            auditoria.pagespeed_mobile = consultar_pagespeed(auditoria.url_final, chave)
            auditoria.problemas = listar_problemas(auditoria)
        except (requests.RequestException, ValueError, KeyError):
            pass  # PageSpeed é opcional; segue sem a nota.
    return auditoria


def dominio(url: str) -> str:
    """Domínio sem 'www.', usado para evitar leads repetidos."""
    url = normalizar_url(url)
    if not url:
        return ""
    host = urlparse(url).netloc.lower().split(":")[0]
    return host[4:] if host.startswith("www.") else host
