# Arena Copy: plataforma de evolução dos alunos do copy trade

Site onde cada aluno acompanha a própria evolução e disputa com os outros: placas por patrimônio, prêmios por lucro, rankings, campeonato por temporada, duelos 1x1 e guerra de clãs.

Abra `index.html` no navegador para ver funcionando com dados de exemplo. É um arquivo só, sem instalação.

## Telas

| Tela | O que mostra |
|---|---|
| **Meu painel** | Placa atual e quanto falta para a próxima, patrimônio, lucro acumulado, lucro do mês, próximo prêmio, gráfico de evolução do patrimônio x total aportado, lucro por mês e **"Sua disputa do mês"** (quem está logo acima, quanto falta para passar e quem vem atrás). |
| **Rankings** | Lucro (R$), Rentabilidade (%), Aportes, Patrimônio e Clãs. Filtro por mês, temporada ou geral. Pódio, setas de quem subiu/caiu e a linha do aluno destacada. |
| **Campeonato** | Temporada com contagem regressiva, premiação, classificação, regras, duelos 1x1 e guerra de clãs. |
| **Placas e prêmios** | Trilha completa de placas (Recruta → Lenda) e lista de prêmios, com quantos alunos já conquistaram cada um. |
| **Hall da fama** | Recordes, campeões de cada mês e feed de conquistas recentes ("Fulano subiu para a placa Ouro"). |

## Regras que geram disputa (já embutidas)

- **Placas pelo patrimônio** (aportes + lucro) e **prêmios pelo lucro acumulado**, como você descreveu.
- **Campeonato por rentabilidade (%)**, não por R$, para conta pequena disputar de igual com conta grande. Aportes entram na base do cálculo, então depositar mais não infla o %.
- **Patrimônio mínimo** (R$ 2.000) para entrar no ranking de rentabilidade e no campeonato.
- **Ranking de aportes** separado, para premiar quem coloca mais capital.
- **Clãs** competem pela média de rentabilidade dos membros, então o tamanho do clã não decide.
- **"Sua disputa"** no painel mostra ao aluno exatamente quanto falta para passar o próximo da fila.

## Como personalizar

Tudo fica no começo do `<script>` em `index.html`:

- `CONFIG.marca`: nome que aparece no topo.
- `CONFIG.placas`: nome, valor mínimo de patrimônio e cor de cada placa.
- `CONFIG.premios`: meta de lucro, nome e detalhe de cada prêmio.
- `CONFIG.campeonato`: nome, meses que contam, data de encerramento, premiação e regras.
- `CONFIG.clas`: nome e cor de cada clã.
- `ALUNOS`: um registro por aluno, com `aportes` e `lucro` mês a mês (na ordem de `CONFIG.meses`).

Os alunos e valores atuais são **fictícios**, só para demonstração.

## Próximos passos para colocar no ar com alunos reais

1. **Dados:** alimentar `ALUNOS` a partir de uma planilha Google (exportada como CSV) ou direto da API da corretora/plataforma de copy (MT4/MT5, myfxbook, etc.).
2. **Login:** cada aluno entra e vê o próprio painel. O seletor "Ver painel como" existe só no modo demonstração.
3. **Hospedagem:** como é um arquivo estático, pode ir para GitHub Pages, Netlify ou Vercel sem custo.
4. **Privacidade (LGPD):** peça consentimento para exibir nome e valores no ranking, ou mostre só apelido e % para quem preferir.
5. **Comunicação:** evite frases que prometam rentabilidade. Mostre resultados passados como histórico, com aviso de que não garantem resultados futuros.
