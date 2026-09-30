"""Linha de comando do agente de prospecção.

Exemplos:
    python -m prospector                                   # rotina diária (usa config.yaml)
    python -m prospector --quantidade 5                    # só 5 leads hoje
    python -m prospector --nicho "clínicas de estética" --cidade "Curitiba - PR"
    python -m prospector --empresa "Clínica Bella" --cidade "Curitiba - PR" --site bella.com.br
    python -m prospector --auditar-site https://exemplo.com.br   # só a auditoria técnica (sem IA)
"""

from __future__ import annotations

import argparse
import logging
import os
import sys
from datetime import date
from pathlib import Path

import anthropic

from .auditoria_site import auditar_site
from .claude import ClienteClaude
from .config import ErroDeConfiguracao, carregar_config
from .pipeline import analisar_empresa, executar_dia


def _argumentos(argv: list[str] | None) -> argparse.Namespace:
    p = argparse.ArgumentParser(prog="prospector", description="Agente de prospecção de leads da agência.")
    p.add_argument("--config", default="config.yaml", help="caminho do config.yaml")
    p.add_argument("--quantidade", type=int, help="quantidade de leads (padrão: leads_por_dia do config)")
    p.add_argument("--nicho", help="força um nicho específico (em vez do rodízio)")
    p.add_argument("--cidade", help="força uma cidade específica (em vez do rodízio)")
    p.add_argument("--data", type=date.fromisoformat, default=date.today(), help="data da rodada (AAAA-MM-DD)")
    p.add_argument("--empresa", help="analisa uma empresa específica em vez de prospectar")
    p.add_argument("--site", default="", help="site da empresa (com --empresa)")
    p.add_argument("--instagram", default="", help="Instagram da empresa (com --empresa)")
    p.add_argument("--auditar-site", metavar="URL", help="roda só a auditoria técnica de um site (não usa IA)")
    p.add_argument("-v", "--verbose", action="store_true", help="mostra mais detalhes no log")
    return p.parse_args(argv)


def _resumo_github(pasta: Path) -> None:
    """Mostra o relatório na página da execução do GitHub Actions."""
    destino = os.environ.get("GITHUB_STEP_SUMMARY")
    relatorio = pasta / "relatorio.md"
    if destino and relatorio.exists():
        with open(destino, "a", encoding="utf-8") as f:
            f.write(relatorio.read_text(encoding="utf-8")[:900_000])


def main(argv: list[str] | None = None) -> int:
    args = _argumentos(argv)
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
        datefmt="%H:%M:%S",
    )
    for barulhento in ("httpx", "httpx2", "urllib3", "anthropic"):
        logging.getLogger(barulhento).setLevel(logging.WARNING)

    if args.auditar_site:
        print(auditar_site(args.auditar_site).resumo())
        return 0

    try:
        cfg = carregar_config(args.config)
    except ErroDeConfiguracao as e:
        print(f"Erro no config: {e}", file=sys.stderr)
        return 2

    cliente = ClienteClaude(cfg.modelo.nome)
    try:
        if args.empresa:
            if not args.cidade:
                print("Informe --cidade junto com --empresa.", file=sys.stderr)
                return 2
            resultado = analisar_empresa(
                cfg, cliente, args.data, args.empresa, args.cidade, args.nicho or "", args.site, args.instagram
            )
        else:
            segmentos = None
            if args.nicho or args.cidade:
                segmentos = [(args.nicho or cfg.prospeccao.nichos[0], args.cidade or cfg.prospeccao.cidades[0])]
            resultado = executar_dia(cfg, cliente, args.data, args.quantidade, segmentos)
    except anthropic.AuthenticationError:
        print("Chave da API do Claude inválida ou ausente. Defina ANTHROPIC_API_KEY.", file=sys.stderr)
        return 3
    except anthropic.PermissionDeniedError as e:
        print(f"A chave da API não tem permissão para esta operação: {e}", file=sys.stderr)
        return 3
    except anthropic.AnthropicError as e:
        print(f"Erro ao falar com a API do Claude: {e}", file=sys.stderr)
        return 1

    _resumo_github(resultado.pasta)
    print(f"\n{len(resultado.leads)} leads analisados, {len(resultado.falhas)} falhas.")
    print(f"Relatório: {resultado.pasta / 'relatorio.md'}")
    for aviso in resultado.avisos:
        print(f"Aviso: {aviso}")
    # Falha "de verdade" só se nada deu certo, para o GitHub avisar por e-mail.
    return 0 if resultado.leads else 1


if __name__ == "__main__":
    sys.exit(main())
