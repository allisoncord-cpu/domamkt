# Agente de Prospecção da Doma

Um agente de IA (Claude) que **todos os dias**:

1. **Encontra empresas** com potencial para virar cliente da agência, fazendo rodízio entre os nichos e cidades definidos no `config.yaml`.
2. **Levanta site, redes sociais e contatos comerciais** (Instagram, Facebook, LinkedIn, TikTok, YouTube, Google Maps, WhatsApp, telefone, e-mail).
3. **Faz a pré-análise do marketing** de cada empresa, dá nota de 0 a 10 por área e **descreve o que precisa melhorar**: site, SEO e Google, Instagram, outras redes, tráfego pago, reputação, identidade visual, conteúdo e conversão.
4. **Indica quais serviços da agência 360° resolvem cada problema** e dá um **score de oportunidade** de 0 a 100, para você saber por onde começar.
5. **Escreve as mensagens do primeiro contato** (WhatsApp, e-mail e direct do Instagram), personalizadas com o que encontrou.

O agente **não envia nada sozinho**. Ele entrega o material pronto e alguém do time revisa e envia (veja [Boas práticas](#boas-práticas-e-lgpd)).

---

## O que você recebe todo dia

Uma pasta `leads/AAAA-MM-DD/` com:

| Arquivo | Para quê |
|---|---|
| `relatorio.md` | Relatório completo, com ranking dos leads, diagnóstico por área, auditoria do site e mensagens prontas. Abra no GitHub para ver formatado. Tem botão **"Abrir no WhatsApp com a mensagem pronta"**. |
| `leads.csv` | Planilha para importar no Google Planilhas, Excel ou CRM, com a coluna `status` já preenchida como "a contatar". |
| `leads.json` | Os mesmos dados em formato técnico, para integrações. |

O relatório também aparece na página da execução, em **Actions → Prospecção diária de leads → (execução do dia)**.

## Como funciona

```
config.yaml ──► 1. Descoberta ──► 2. Auditoria do site ──► 3. Pesquisa ──► 4. Diagnóstico ──► leads/AAAA-MM-DD/
               (busca web)        (código, sem IA)          (busca web)     (+ mensagens)
```

1. **Descoberta:** o Claude pesquisa na web empresas do nicho e da cidade do dia que se encaixam no perfil ideal, e ignora as que já foram prospectadas (histórico em `data/historico.json`).
2. **Auditoria técnica do site:** o código mede fatos objetivos: HTTPS, velocidade, versão para celular, SEO básico, Pixel da Meta, Google Analytics/Tag Manager, botão de WhatsApp, ano do rodapé, contatos e redes linkadas. Se você configurar a chave do Google PageSpeed, entra também a nota de desempenho mobile de 0 a 100.
3. **Pesquisa:** o Claude busca e lê site, redes sociais, Google Maps, avaliações, anúncios e concorrentes, e anota tudo com as fontes.
4. **Diagnóstico e abordagem:** o Claude transforma a pesquisa em um diagnóstico estruturado, com notas, melhorias, serviços recomendados, score e mensagens.

---

## Configuração (uma vez só, uns 10 minutos)

### 1. Crie a chave da API do Claude

1. Acesse <https://console.anthropic.com>, crie uma conta e adicione créditos em **Billing**.
2. Em **API Keys**, clique em **Create Key** e copie a chave (começa com `sk-ant-`).

### 2. Cadastre a chave no GitHub

No repositório, abra **Settings → Secrets and variables → Actions → New repository secret**:

| Nome | Valor | Obrigatório? |
|---|---|---|
| `ANTHROPIC_API_KEY` | a chave copiada acima | Sim |
| `PAGESPEED_API_KEY` | chave do Google PageSpeed Insights ([como criar](https://developers.google.com/speed/docs/insights/v5/get-started#APIKey)), gratuita | Opcional, adiciona a nota de velocidade do site |

### 3. Ajuste o `config.yaml`

Edite direto pelo GitHub (ícone de lápis) e revise principalmente:

- `agencia.cidade_base`, `servicos`, `diferenciais`, `assinatura` e `oferta_de_entrada`
- `prospeccao.cidades` e `prospeccao.nichos`: **onde** e **quem** prospectar
- `prospeccao.leads_por_dia`: quantidade de leads por dia (padrão: 10)

### 4. Teste agora

Vá em **Actions → Prospecção diária de leads → Run workflow**. Você pode deixar os campos vazios ou pedir, por exemplo, 3 leads de um nicho e cidade específicos. Quando a execução termina (leva de 10 a 40 minutos), o relatório aparece na pasta `leads/`.

A partir daí ele roda sozinho **todo dia às 07:17** (horário de Brasília). Para mudar o horário ou rodar só em dias úteis, edite a linha `cron` em `.github/workflows/prospeccao-diaria.yml`. Por exemplo, `"17 10 * * 1-5"` roda de segunda a sexta.

> O agendamento do GitHub só funciona na **branch padrão** do repositório. Se este código estiver em outra branch, faça o merge dele na principal.

---

## Analisar uma empresa específica

Chegou uma indicação ou um lead pelo Instagram? Dá para gerar a pré-análise só dela, rodando localmente:

```bash
python -m prospector --empresa "Clínica Bella" --cidade "Curitiba - PR" --site bellaclinica.com.br --instagram @bellaclinica
```

O resultado vai para `leads/AAAA-MM-DD-clinica-bella/`.

## Rodar no seu computador

```bash
python -m venv .venv && source .venv/bin/activate   # no Windows: .venv\Scripts\activate
pip install -r requirements.txt
export ANTHROPIC_API_KEY="sk-ant-..."                # no Windows: set ANTHROPIC_API_KEY=sk-ant-...

python -m prospector                                  # rotina do dia (usa o config.yaml)
python -m prospector --quantidade 3                   # só 3 leads
python -m prospector --nicho "imobiliárias" --cidade "Campinas - SP"
python -m prospector --auditar-site https://exemplo.com.br   # só a auditoria técnica, não usa IA nem gasta créditos
```

Para rodar os testes (não usam a API): `pip install -r requirements-dev.txt && python -m pytest`.

---

## Custos

O custo vem da API do Claude (tokens e buscas web). Com o modelo padrão (`claude-opus-5-5`, o mais capaz para esse tipo de pesquisa), a estimativa fica **na faixa de US$ 0,50 a US$ 1,00 por lead analisado**. O rodapé de cada relatório mostra o **custo estimado real do dia**. Confira depois da primeira execução.

Para gastar menos, mexa no `config.yaml`:

- `leads_por_dia`: menos leads por dia.
- `max_buscas_por_lead` e `max_leituras_por_lead`: menos buscas por lead.
- `esforco_*`: trocar `high` por `medium` diminui o raciocínio e o custo.
- `modelo.nome: "claude-sonnet-5-5"`: modelo mais barato, cerca de metade do preço, com análise um pouco menos profunda.

Se o modelo principal recusar algum pedido, a API refaz automaticamente em um modelo reserva (*fallback*), sem você precisar fazer nada.

---

## Limitações

- **Instagram e LinkedIn** bloqueiam leitura automática. Nesses casos o agente usa o que aparece nos resultados de busca (bio, seguidores, posts recentes) e avisa o que não conseguiu verificar. O campo `confianca_dos_dados` indica o quanto dá para confiar.
- **Anúncios ativos** (Biblioteca de Anúncios da Meta) nem sempre podem ser confirmados. O agente usa pistas, como o Pixel da Meta no site, e marca como "não verificado" quando não consegue.
- A IA pode errar. Sempre **confira os contatos e os dados principais** antes de usar na conversa.

## Boas práticas e LGPD

- O agente coleta apenas **dados comerciais públicos** das empresas. Nome de sócio ou gestor só entra quando a própria pessoa divulga em contexto profissional (site da empresa, LinkedIn, imprensa).
- A prospecção B2B pode se apoiar no **legítimo interesse** (LGPD, art. 7º, IX), desde que a abordagem seja relevante, identificada e **permita recusar**. Por isso os e-mails já saem com uma linha de opt-out.
- Quem pedir para não receber mais contato deve ir para uma lista de exclusão. Registre em `data/historico.json` ou no seu CRM.
- **Não automatize o envio** pelo WhatsApp ou Instagram. Disparos automáticos violam os termos dessas plataformas e podem **bloquear o número ou o perfil da agência**. Envie manualmente, com calma, e personalize.

---

## Estrutura do projeto

```
config.yaml                     ← tudo que você personaliza
prospector/
  pipeline.py                   ← orquestra o dia (descoberta → análise → relatório)
  prompts.py                    ← instruções dadas à IA (tom, critérios, mensagens)
  auditoria_site.py             ← auditoria técnica do site (sem IA)
  claude.py                     ← comunicação com a API do Claude (busca web + saída estruturada)
  modelos.py                    ← formato do diagnóstico (áreas, notas, mensagens)
  historico.py                  ← evita prospectar a mesma empresa de novo
  relatorio.py                  ← gera relatorio.md, leads.csv e leads.json
data/historico.json             ← empresas já prospectadas
leads/                          ← relatórios diários
.github/workflows/              ← agendamento diário e testes
tests/                          ← testes automáticos (sem gastar API)
```

Para mudar o **jeito que a IA analisa ou escreve as mensagens**, edite `prospector/prompts.py`. Para incluir ou tirar campos do diagnóstico, edite `prospector/modelos.py`.
