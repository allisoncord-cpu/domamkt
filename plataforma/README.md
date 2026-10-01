# Legião Legatus: plataforma de evolução dos alunos do copy trade

Site da Legatus Group FX onde cada aluno acompanha a própria evolução e disputa com os outros. Tudo em dólar (US$).

Abra `index.html` no navegador para ver funcionando com dados de exemplo. É um arquivo só, sem instalação.

## A lógica da disputa

No copy trade a rentabilidade é a mesma para todos, então a competição é por **aporte** e por **saldo na conta**:

- **Quadros (placas) pelo saldo na conta:** Smart Move US$ 10K (Esmeralda), On Track US$ 25K (Safira), Momentum US$ 50K (Rubi), Next Millionaire US$ 100K (Ametista) e Millionaire US$ 200K (Ônix).
- **Prêmios pelo lucro acumulado.**
- **Copa dos Aportes:** campeonato por temporada. Vence quem fizer o maior aporte líquido (depósitos menos saques).
- **Duelos 1x1** entre vizinhos de classificação, mostrando quanto falta para virar.
- **Guerra de Clãs** pelo aporte somado dos membros.

## Telas

| Tela | O que mostra |
|---|---|
| **Meu painel** | Quadro atual com o nome do aluno, barra até o próximo quadro, saldo, aporte na Copa, lucro, resultado do copy no mês, **"Sua disputa na Copa"** (quanto aportar para passar quem está na frente), gráficos de saldo e de aportes. |
| **Copa dos Aportes** | Contagem regressiva, premiação, classificação, regras, duelos e clãs. |
| **Rankings** | Aportes, Saldo na conta, Lucro e Clãs, com filtro por mês, temporada ou geral. |
| **Quadros e prêmios** | Os 5 quadros, quais o aluno já conquistou, quanto falta e quantos alunos já têm cada um. Lista de prêmios por lucro. |
| **Hall da fama** | Recordes, campeões de aporte de cada mês e feed de conquistas. |

## Como personalizar

Tudo fica no começo do `<script>` em `index.html`:

- `CONFIG.placas`: nome, valor mínimo, pedra, cor, frase e tamanho de cada quadro.
- `CONFIG.premios`: meta de lucro e prêmio.
- `CONFIG.campeonato`: nome, meses que contam, data de encerramento, aporte mínimo, premiação e regras.
- `CONFIG.clas`: nome e cor de cada clã.
- `ALUNOS`: um registro por aluno, com `aportes` e `lucro` mês a mês em US$ (e `saques`, opcional).

Os alunos e valores atuais são **fictícios**, só para demonstração.

## Próximos passos para colocar no ar

1. **Dados reais:** puxar saldo, depósitos e saques da corretora/plataforma de copy (MT4/MT5, myfxbook) ou de uma planilha Google.
2. **Login:** cada aluno vê o próprio painel. O seletor "Ver painel como" existe só no modo demonstração.
3. **Hospedagem:** arquivo estático, pode ir para GitHub Pages, Netlify ou Vercel.
4. **Privacidade (LGPD):** pedir consentimento para mostrar nome e valores, ou exibir só apelido.
5. **Comunicação:** não prometer rentabilidade; resultados passados não garantem resultados futuros.
