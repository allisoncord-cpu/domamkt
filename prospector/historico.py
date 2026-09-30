"""Histórico de empresas já prospectadas, para não repetir leads."""

from __future__ import annotations

import json
import re
import unicodedata
from datetime import date, timedelta
from pathlib import Path

from .auditoria_site import dominio


def slug(texto: str) -> str:
    texto = unicodedata.normalize("NFKD", texto or "").encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", "-", texto.lower()).strip("-")


def handle_instagram(valor: str) -> str:
    valor = (valor or "").strip()
    m = re.search(r"instagram\.com/([A-Za-z0-9_.]+)", valor, re.I)
    if m:
        return m.group(1).lower()
    # Sem URL, só aceita "@perfil" (evita tratar "nenhum" ou "n/a" como perfil).
    return valor[1:].lower() if re.fullmatch(r"@[A-Za-z0-9_.]{2,30}", valor) else ""


def cidade_curta(cidade: str) -> str:
    """'São Paulo - SP' -> 'sao-paulo' (mantém hífens do nome, como em Embu-Guaçu)."""
    return slug(re.split(r"\s+-\s+|/|,", cidade or "")[0])


def chaves(nome: str, cidade: str, site: str = "", instagram: str = "") -> list[str]:
    """Identificadores de uma empresa: domínio, @ do Instagram e nome+cidade."""
    resultado = []
    if d := dominio(site):
        resultado.append(f"site:{d}")
    if h := handle_instagram(instagram):
        resultado.append(f"ig:{h}")
    if nome_slug := slug(nome):
        resultado.append(f"nome:{nome_slug}|{cidade_curta(cidade)}")
    return resultado


class Historico:
    def __init__(self, caminho: Path, dias_para_reprospectar: int = 120):
        self.caminho = Path(caminho)
        self.dias = dias_para_reprospectar
        self.leads: dict[str, dict] = {}
        if self.caminho.exists():
            dados = json.loads(self.caminho.read_text(encoding="utf-8") or "{}")
            self.leads = dados.get("leads", {})

    def ja_prospectado(self, nome: str, cidade: str, site: str = "", instagram: str = "", hoje: date | None = None) -> bool:
        limite = (hoje or date.today()) - timedelta(days=self.dias)
        for chave in chaves(nome, cidade, site, instagram):
            registro = self.leads.get(chave)
            if registro and date.fromisoformat(registro["data"]) > limite:
                return True
        return False

    def nomes_recentes(self, cidade: str | None = None, hoje: date | None = None) -> list[str]:
        """Nomes prospectados dentro da janela (opcionalmente só da cidade), para o agente evitar."""
        sufixo = f"|{cidade_curta(cidade)}" if cidade else ""
        limite = (hoje or date.today()) - timedelta(days=self.dias)
        nomes = []
        for chave, registro in self.leads.items():
            if not chave.startswith("nome:") or not chave.endswith(sufixo):
                continue
            if date.fromisoformat(registro["data"]) > limite:
                nomes.append(registro["nome"])
        return sorted(set(nomes))

    def registrar(self, nome: str, cidade: str, site: str = "", instagram: str = "", hoje: date | None = None) -> None:
        registro = {"nome": nome, "cidade": cidade, "data": (hoje or date.today()).isoformat()}
        for chave in chaves(nome, cidade, site, instagram):
            self.leads[chave] = registro

    def salvar(self) -> None:
        self.caminho.parent.mkdir(parents=True, exist_ok=True)
        conteudo = {"leads": dict(sorted(self.leads.items()))}
        self.caminho.write_text(json.dumps(conteudo, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
