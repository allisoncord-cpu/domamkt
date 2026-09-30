"""Comunicação com a API do Claude.

Duas operações:
- `pesquisar`: o Claude usa busca e leitura web (ferramentas do lado da Anthropic)
  e devolve anotações em texto com as fontes.
- `estruturar`: o Claude transforma anotações em um objeto Pydantic validado
  (structured outputs), para gerar relatório/CSV sem erro de formato.
"""

from __future__ import annotations

import logging
import threading
from dataclasses import dataclass, field
from typing import TypeVar

import anthropic
from pydantic import BaseModel

log = logging.getLogger(__name__)

# Se o modelo principal recusar um pedido, a API refaz automaticamente no
# modelo reserva recomendado pela Anthropic (server-side fallback).
BETAS = ["server-side-fallback-2026-07-01"]
FALLBACKS = "default"
MAX_CONTINUACOES = 5
LOCALIZACAO_BR = {"type": "approximate", "country": "BR", "timezone": "America/Sao_Paulo"}

# Preços aproximados (US$ por 1 milhão de tokens) só para a estimativa de custo do relatório.
PRECOS = {
    "claude-opus-5-5": (4.00, 20.00),
    "claude-sonnet-5-5": (2.00, 10.00),
    "claude-fable-5-1": (10.00, 50.00),
}
PRECO_BUSCA = 10.00 / 1000  # US$ por busca web

M = TypeVar("M", bound=BaseModel)


class RecusaDoModelo(RuntimeError):
    """O modelo (e o reserva) se recusou a responder."""


@dataclass
class Uso:
    tokens_entrada: int = 0
    tokens_saida: int = 0
    tokens_cache_leitura: int = 0
    buscas_web: int = 0
    leituras_web: int = 0
    chamadas: int = 0
    _trava: threading.Lock = field(default_factory=threading.Lock, repr=False)

    def somar(self, resposta) -> None:
        u = resposta.usage
        with self._trava:
            self.chamadas += 1
            self.tokens_entrada += (u.input_tokens or 0) + (getattr(u, "cache_creation_input_tokens", 0) or 0)
            self.tokens_cache_leitura += getattr(u, "cache_read_input_tokens", 0) or 0
            self.tokens_saida += u.output_tokens or 0
            servidor = getattr(u, "server_tool_use", None)
            if servidor is not None:
                self.buscas_web += getattr(servidor, "web_search_requests", 0) or 0
                self.leituras_web += getattr(servidor, "web_fetch_requests", 0) or 0

    def custo_estimado(self, modelo: str) -> float | None:
        if modelo not in PRECOS:
            return None
        entrada, saida = PRECOS[modelo]
        return (
            self.tokens_entrada * entrada / 1e6
            + self.tokens_cache_leitura * entrada * 0.1 / 1e6
            + self.tokens_saida * saida / 1e6
            + self.buscas_web * PRECO_BUSCA
        )


@dataclass
class ResultadoPesquisa:
    texto: str
    fontes: list[str]


def _fontes(conteudo) -> list[str]:
    """Coleta URLs citadas nas respostas e páginas lidas pelo modelo."""
    urls: list[str] = []
    for bloco in conteudo:
        tipo = getattr(bloco, "type", "")
        if tipo == "text":
            for citacao in getattr(bloco, "citations", None) or []:
                url = getattr(citacao, "url", None)
                if url:
                    urls.append(url)
        elif tipo == "web_fetch_tool_result":
            url = getattr(getattr(bloco, "content", None), "url", None)
            if url:
                urls.append(url)
    return list(dict.fromkeys(urls))


class ClienteClaude:
    def __init__(self, modelo: str, client: anthropic.Anthropic | None = None):
        self.modelo = modelo
        self.client = client or anthropic.Anthropic(max_retries=4)
        self.uso = Uso()

    def _checar_recusa(self, resposta) -> None:
        if resposta.stop_reason == "refusal":
            detalhes = getattr(resposta, "stop_details", None)
            categoria = getattr(detalhes, "category", None) if detalhes else None
            raise RecusaDoModelo(f"O modelo recusou o pedido (categoria: {categoria}).")

    def pesquisar(
        self,
        sistema: str,
        pedido: str,
        esforco: str,
        max_buscas: int,
        max_leituras: int,
    ) -> ResultadoPesquisa:
        ferramentas = [
            {"type": "web_search_20260209", "name": "web_search", "max_uses": max_buscas, "user_location": LOCALIZACAO_BR},
            {"type": "web_fetch_20260209", "name": "web_fetch", "max_uses": max_leituras},
        ]
        mensagens: list[dict] = [{"role": "user", "content": pedido}]
        textos: list[str] = []
        fontes: list[str] = []

        for _ in range(MAX_CONTINUACOES + 1):
            with self.client.beta.messages.stream(
                model=self.modelo,
                max_tokens=32000,
                system=sistema,
                messages=mensagens,
                tools=ferramentas,
                thinking={"type": "adaptive"},
                output_config={"effort": esforco},
                cache_control={"type": "ephemeral"},
                betas=BETAS,
                fallbacks=FALLBACKS,
            ) as stream:
                resposta = stream.get_final_message()
            self.uso.somar(resposta)
            self._checar_recusa(resposta)

            textos += [b.text for b in resposta.content if b.type == "text"]
            fontes += _fontes(resposta.content)

            if resposta.stop_reason != "pause_turn":
                break
            # A busca no servidor atingiu o limite de iterações: reenviamos a
            # conversa e a API continua de onde parou (sem mensagem extra).
            mensagens.append({"role": "assistant", "content": resposta.content})
        else:
            log.warning("Pesquisa interrompida após %s continuações.", MAX_CONTINUACOES)

        if resposta.stop_reason == "max_tokens":
            log.warning("Pesquisa cortada por limite de tokens; usando o que foi obtido.")

        return ResultadoPesquisa(texto="".join(textos).strip(), fontes=list(dict.fromkeys(fontes)))

    def estruturar(self, sistema: str, pedido: str, formato: type[M], esforco: str) -> M:
        with self.client.beta.messages.stream(
            model=self.modelo,
            max_tokens=32000,
            system=sistema,
            messages=[{"role": "user", "content": pedido}],
            thinking={"type": "adaptive"},
            output_config={"effort": esforco},
            output_format=formato,
            betas=BETAS,
            fallbacks=FALLBACKS,
        ) as stream:
            resposta = stream.get_final_message()
        self.uso.somar(resposta)
        self._checar_recusa(resposta)
        if resposta.stop_reason == "max_tokens":
            raise RuntimeError("Resposta estruturada cortada por limite de tokens.")
        if resposta.parsed_output is None:
            raise RuntimeError("O modelo não devolveu a resposta no formato esperado.")
        return resposta.parsed_output
