"""Leitura e validação do config.yaml."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import yaml

ESFORCOS_VALIDOS = {"low", "medium", "high", "xhigh", "max"}


class ErroDeConfiguracao(ValueError):
    pass


@dataclass
class Agencia:
    nome: str
    descricao: str
    cidade_base: str
    servicos: list[str]
    diferenciais: list[str]
    tom_de_voz: str
    assinatura: str
    oferta_de_entrada: str


@dataclass
class Prospeccao:
    leads_por_dia: int
    segmentos_por_dia: int
    cidades: list[str]
    nichos: list[str]
    perfil_ideal: list[str] = field(default_factory=list)
    evitar: list[str] = field(default_factory=list)


@dataclass
class Modelo:
    nome: str = "claude-opus-5-5"
    esforco_descoberta: str = "high"
    esforco_pesquisa: str = "high"
    esforco_analise: str = "high"
    max_buscas_descoberta: int = 15
    max_buscas_por_lead: int = 12
    max_leituras_por_lead: int = 8
    paralelismo: int = 3


@dataclass
class Saida:
    pasta_leads: str = "leads"
    arquivo_historico: str = "data/historico.json"
    dias_para_reprospectar: int = 120


@dataclass
class Config:
    agencia: Agencia
    prospeccao: Prospeccao
    modelo: Modelo
    saida: Saida
    raiz: Path

    @property
    def pasta_leads(self) -> Path:
        return self.raiz / self.saida.pasta_leads

    @property
    def arquivo_historico(self) -> Path:
        return self.raiz / self.saida.arquivo_historico


def _lista(valor, nome: str) -> list[str]:
    if not isinstance(valor, list) or not all(isinstance(v, str) and v.strip() for v in valor):
        raise ErroDeConfiguracao(f"'{nome}' precisa ser uma lista de textos.")
    return [v.strip() for v in valor]


def carregar_config(caminho: str | Path) -> Config:
    caminho = Path(caminho)
    if not caminho.exists():
        raise ErroDeConfiguracao(f"Arquivo de configuração não encontrado: {caminho}")
    dados = yaml.safe_load(caminho.read_text(encoding="utf-8")) or {}

    try:
        ag = dados["agencia"]
        agencia = Agencia(
            nome=ag["nome"],
            descricao=ag["descricao"],
            cidade_base=ag.get("cidade_base", "Brasil"),
            servicos=_lista(ag["servicos"], "agencia.servicos"),
            diferenciais=_lista(ag["diferenciais"], "agencia.diferenciais") if ag.get("diferenciais") else [],
            tom_de_voz=ag.get("tom_de_voz", "próximo e consultivo"),
            assinatura=ag.get("assinatura", ag["nome"]),
            oferta_de_entrada=ag.get("oferta_de_entrada", "um diagnóstico gratuito"),
        )

        pr = dados["prospeccao"]
        prospeccao = Prospeccao(
            leads_por_dia=int(pr.get("leads_por_dia", 10)),
            segmentos_por_dia=int(pr.get("segmentos_por_dia", 2)),
            cidades=_lista(pr["cidades"], "prospeccao.cidades"),
            nichos=_lista(pr["nichos"], "prospeccao.nichos"),
            perfil_ideal=_lista(pr["perfil_ideal"], "prospeccao.perfil_ideal") if pr.get("perfil_ideal") else [],
            evitar=_lista(pr["evitar"], "prospeccao.evitar") if pr.get("evitar") else [],
        )
    except KeyError as e:
        raise ErroDeConfiguracao(f"Campo obrigatório ausente no config: {e}") from e

    modelo = Modelo(**(dados.get("modelo") or {}))
    saida = Saida(**(dados.get("saida") or {}))

    if prospeccao.leads_por_dia < 1:
        raise ErroDeConfiguracao("'prospeccao.leads_por_dia' precisa ser pelo menos 1.")
    if prospeccao.segmentos_por_dia < 1:
        raise ErroDeConfiguracao("'prospeccao.segmentos_por_dia' precisa ser pelo menos 1.")
    for nome in ("esforco_descoberta", "esforco_pesquisa", "esforco_analise"):
        if getattr(modelo, nome) not in ESFORCOS_VALIDOS:
            raise ErroDeConfiguracao(
                f"'modelo.{nome}' deve ser um de: {', '.join(sorted(ESFORCOS_VALIDOS))}."
            )
    if modelo.paralelismo < 1:
        modelo.paralelismo = 1

    return Config(agencia=agencia, prospeccao=prospeccao, modelo=modelo, saida=saida, raiz=caminho.parent.resolve())
