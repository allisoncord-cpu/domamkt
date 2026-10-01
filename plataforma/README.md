# Legião Legatus: portal do aluno e painel de administração

Portal da Legatus Group FX (copy trade na RoboForex). Todos os valores em dólar (US$).

Abra `index.html` no navegador. Na tela de entrada, escolha **Administrador** ou um aluno.
Modo demonstração: não pede senha e os dados ficam salvos só no navegador de quem abriu.

## Como os dados se atualizam

O sistema não guarda "a placa do aluno". Ele guarda **lançamentos com data** e calcula o resto:

| De onde vem | Quem faz | Efeito |
|---|---|---|
| **Comprovante de aporte** | O aluno envia o print do depósito na RoboForex; o admin aprova | Entra como aporte no saldo, nos rankings e na Copa |
| **Resultado do copy** | O admin lança um % por semana ou por mês | Atualiza o saldo de **todos** os alunos de uma vez (a rentabilidade é igual para todos) |
| **Lançamento manual** | O admin, na ficha do aluno | Aporte, saque ou correção de saldo (quando o aluno manda print do saldo atual) |
| **Cadastro** | O admin cadastra o aluno com total já aportado e saldo atual | Ponto de partida; não conta para a Copa |

Saldo = aportes − saques, corrigido pelos resultados do copy e pelas correções de saldo.
Lucro = saldo − total aportado. Quadro = maior saldo já atingido.

## Telas do aluno

- **Meu painel:** quadro atual, quanto falta para o próximo, saldo, lucro, posição na Copa e quanto aportar para passar o próximo.
- **Informar aporte:** valor, data, saldo após o depósito (opcional) e o print.
- **Meus envios:** situação de cada comprovante (em análise, aprovado ou recusado com o motivo).
- **Copa dos Aportes, Rankings, Quadros e prêmios, Hall da fama.**

## Telas do administrador

- **Visão geral:** comprovantes pendentes, total aportado na Copa, quadros a entregar e aviso para lançar o resultado do copy.
- **Aprovações:** fila de comprovantes com o print ampliável. Dá para ajustar o valor antes de aprovar, informar o saldo, ou recusar com motivo.
- **Alunos:** busca, cadastro e ficha de cada aluno com todos os lançamentos.
- **Resultado do copy:** lança o % do período e mostra o impacto no saldo da Legião.
- **Quadros:** quem conquistou cada quadro e a situação (a produzir, em produção, enviado, entregue).

## Personalizar

No começo do `<script>` em `index.html`, em `CONFIG`: quadros, prêmios, datas e premiação da Copa e clãs.

## Para colocar no ar com os alunos

A demonstração guarda tudo no navegador. Para uso real, falta:

1. **Banco de dados e login** (por exemplo Supabase, que tem plano gratuito): cada aluno entra com e-mail e senha e só vê o próprio painel e envios; só o admin aprova.
2. **Armazenamento dos prints** no mesmo serviço.
3. **Hospedagem** do site (Netlify, Vercel ou GitHub Pages) com domínio próprio.
4. **Aviso de privacidade (LGPD)** para mostrar nome e valores no ranking.
