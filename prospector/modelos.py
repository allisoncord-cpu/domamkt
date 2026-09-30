"""Estruturas de dados que o agente produz (validadas com Pydantic).

Esses modelos também viram o schema de "structured outputs" enviado ao Claude,
então a resposta da análise sempre chega no formato certo.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

AREAS = Literal[
    "Site",
    "SEO e Google",
    "Instagram",
    "Outras redes sociais",
    "Tráfego pago",
    "Reputação e avaliações",
    "Identidade visual e marca",
    "Conteúdo",
    "Conversão e atendimento",
]


# ---------------------------------------------------------------------------
# Etapa 1: descoberta
# ---------------------------------------------------------------------------


class Candidato(BaseModel):
    nome: str = Field(description="Nome comercial da empresa")
    nicho: str
    cidade: str = Field(description="Cidade - UF")
    site: str = Field(description="URL do site oficial, ou string vazia se não tiver")
    instagram: str = Field(description="URL ou @ do Instagram, ou string vazia se não encontrado")
    motivo: str = Field(description="Em 1 frase: por que parece uma boa oportunidade para a agência")


class ListaCandidatos(BaseModel):
    candidatos: list[Candidato]


# ---------------------------------------------------------------------------
# Etapa 3: análise do lead
# ---------------------------------------------------------------------------


class Contatos(BaseModel):
    site: str = Field(description="URL do site ou ''")
    instagram: str = Field(description="URL do perfil ou ''")
    facebook: str = Field(description="URL da página ou ''")
    linkedin: str = Field(description="URL da página da empresa ou ''")
    tiktok: str = Field(description="URL do perfil ou ''")
    youtube: str = Field(description="URL do canal ou ''")
    google_meu_negocio: str = Field(description="Link do perfil no Google Maps ou ''")
    whatsapp: str = Field(description="Número ou link de WhatsApp comercial ou ''")
    telefone: str = Field(description="Telefone comercial ou ''")
    email: str = Field(description="E-mail comercial ou ''")
    endereco: str = Field(description="Endereço comercial ou ''")
    decisor: str = Field(
        description="Nome e cargo de sócio/gestor SOMENTE se divulgado publicamente em contexto profissional; senão ''"
    )


class AvaliacaoArea(BaseModel):
    area: AREAS
    nota: int = Field(ge=0, le=10, description="0 = inexistente/péssimo, 10 = excelente")
    situacao_atual: str = Field(description="O que foi observado, de forma objetiva")
    o_que_melhorar: list[str] = Field(description="Melhorias concretas e acionáveis")
    evidencias: list[str] = Field(description="Fatos/URLs que sustentam a avaliação")


class AnaliseLead(BaseModel):
    empresa: str
    segmento: str
    cidade: str
    resumo_empresa: str = Field(description="2-3 frases sobre o negócio, público e posicionamento")
    porte_estimado: Literal["micro", "pequena", "média", "grande", "não identificado"]
    contatos: Contatos
    avaliacoes: list[AvaliacaoArea] = Field(description="Uma avaliação por área analisada")
    pontos_fortes: list[str]
    principais_oportunidades: list[str] = Field(
        description="As 3 a 5 melhorias com maior impacto no faturamento, em ordem de prioridade"
    )
    servicos_recomendados: list[str] = Field(description="Serviços da agência que resolvem as oportunidades")
    sinais_de_investimento: list[str] = Field(
        description="Indícios de que a empresa tem verba/interesse em marketing (anúncios, várias unidades, etc.)"
    )
    concorrentes_referencia: list[str] = Field(
        description="1-3 concorrentes locais com marketing melhor, usados como referência na conversa"
    )
    score_oportunidade: int = Field(
        ge=0, le=100, description="Chance de virar cliente x tamanho da oportunidade (100 = lead quentíssimo)"
    )
    prioridade: Literal["alta", "média", "baixa"]
    gancho_abordagem: str = Field(description="O argumento mais forte para abrir a conversa")
    mensagem_whatsapp: str
    email_assunto: str
    email_corpo: str
    mensagem_direct_instagram: str
    confianca_dos_dados: Literal["alta", "média", "baixa"]
    observacoes: str = Field(description="Ressalvas, dados não verificados ou alertas para quem vai abordar")
    fontes: list[str] = Field(description="URLs consultadas que sustentam a análise")
