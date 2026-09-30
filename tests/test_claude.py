"""Testa o laço de chamadas ao Claude com um cliente falso (sem gastar API)."""

from types import SimpleNamespace as NS

import pytest

from prospector.claude import ClienteClaude, RecusaDoModelo
from prospector.modelos import ListaCandidatos


def _uso(buscas=0):
    return NS(input_tokens=1000, output_tokens=200, cache_creation_input_tokens=0, cache_read_input_tokens=0,
              server_tool_use=NS(web_search_requests=buscas, web_fetch_requests=0))


def _texto(t, urls=()):
    return NS(type="text", text=t, citations=[NS(url=u) for u in urls])


class StreamFalso:
    def __init__(self, resposta):
        self.resposta = resposta

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False

    def get_final_message(self):
        return self.resposta


class AnthropicFalso:
    def __init__(self, respostas):
        self.respostas = list(respostas)
        self.chamadas = []
        self.beta = NS(messages=NS(stream=self._stream))

    def _stream(self, **kwargs):
        self.chamadas.append({**kwargs, "messages": list(kwargs["messages"])})
        return StreamFalso(self.respostas.pop(0))


def test_pesquisar_continua_apos_pause_turn_e_junta_fontes():
    pausa = NS(stop_reason="pause_turn", usage=_uso(5),
               content=[_texto("Parte 1. ", ["https://a.com"]), NS(type="server_tool_use")])
    fim = NS(stop_reason="end_turn", usage=_uso(3),
             content=[_texto("Parte 2.", ["https://b.com", "https://a.com"]),
                      NS(type="web_fetch_tool_result", content=NS(url="https://c.com"))])
    falso = AnthropicFalso([pausa, fim])
    cliente = ClienteClaude("claude-opus-5-5", client=falso)

    r = cliente.pesquisar("sistema", "pedido", esforco="high", max_buscas=7, max_leituras=4)

    assert r.texto == "Parte 1. Parte 2."
    assert r.fontes == ["https://a.com", "https://b.com", "https://c.com"]
    assert len(falso.chamadas) == 2
    # a continuação reenvia a resposta pausada, sem inventar mensagem de usuário
    segunda = falso.chamadas[1]["messages"]
    assert [m["role"] for m in segunda] == ["user", "assistant"]
    assert segunda[1]["content"] is pausa.content

    primeira = falso.chamadas[0]
    tipos = {f["type"]: f for f in primeira["tools"]}
    assert tipos["web_search_20260209"]["max_uses"] == 7
    assert tipos["web_fetch_20260209"]["max_uses"] == 4
    assert primeira["model"] == "claude-opus-5-5"
    assert primeira["output_config"] == {"effort": "high"}
    assert primeira["fallbacks"] == "default"
    assert primeira["betas"] == ["server-side-fallback-2026-07-01"]

    assert cliente.uso.chamadas == 2 and cliente.uso.buscas_web == 8
    assert cliente.uso.custo_estimado("claude-opus-5-5") > 0


def test_pesquisar_levanta_erro_em_recusa():
    recusa = NS(stop_reason="refusal", usage=_uso(), content=[], stop_details=NS(category="cyber"))
    cliente = ClienteClaude("claude-opus-5-5", client=AnthropicFalso([recusa]))
    with pytest.raises(RecusaDoModelo):
        cliente.pesquisar("s", "p", esforco="high", max_buscas=1, max_leituras=1)


def test_estruturar_devolve_objeto_validado():
    lista = ListaCandidatos(candidatos=[])
    resposta = NS(stop_reason="end_turn", usage=_uso(), content=[], parsed_output=lista)
    falso = AnthropicFalso([resposta])
    cliente = ClienteClaude("claude-opus-5-5", client=falso)

    assert cliente.estruturar("s", "p", ListaCandidatos, esforco="low") is lista
    assert falso.chamadas[0]["output_format"] is ListaCandidatos
    assert "tools" not in falso.chamadas[0]


def test_estruturar_falha_quando_corta_por_tokens():
    resposta = NS(stop_reason="max_tokens", usage=_uso(), content=[], parsed_output=None)
    cliente = ClienteClaude("claude-opus-5-5", client=AnthropicFalso([resposta]))
    with pytest.raises(RuntimeError):
        cliente.estruturar("s", "p", ListaCandidatos, esforco="low")
