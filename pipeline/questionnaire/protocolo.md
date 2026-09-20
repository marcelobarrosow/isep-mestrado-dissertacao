# Protocolo do estudo (como correu)

Fonte de verdade para replicação: o instrumento em `site/` (PHP + MariaDB) e os capítulos 3–4 da dissertação. O texto de consentimento canónico está em `site/lang/pt.php` e `site/lang/en.php` (`consent_body`); não se duplica aqui.

## Instrumento

Questionário online bilingue (português / inglês), desenvolvido para este estudo. Fluxo:

1. Consentimento informado (`consent.php`), adultos ≥ 18 anos.
2. Item de prática (não conta para o mínimo).
3. Bloco mínimo de cerca de 24 itens cegos, Likert 1–7 de empatia percebida.
4. Oferta de continuar com mais itens do catálogo (`continue_offer.php`) ou concluir.
5. Verificação de atenção (alvo fixo: valor 2).
6. Agradecimento (`thanks.php`). Não há regresso a itens depois da atenção.

Não há passo demográfico (idade, sexo, nível de inglês). Cada classificação é gravada de imediato. A sessão retoma no mesmo browser sem criar outro participante.

## Recrutamento e filtro

Amostra de conveniência (bola de neve, rede pessoal e académica / TMDEI–ISEP). Sem selecção além da idade e do consentimento.

| Contagem | N |
|---|---|
| Inícios (≥ 1 classificação) | 156 |
| Conclusões | 63 |
| Filtro estrito (atenção correcta, ritmo não demasiado rápido) | 52 |
| Classificações Likert na análise principal | 2016 |

Exclusão: consentimento recusado; falha no item de atenção; ritmo relativo demasiado rápido (mediana do item − 2,5 × DAM). Não se usa a duração total da sessão.

## Rotação

96 células (12 estímulos × 4 épocas × 2 condições). A ordem do bloco mínimo e dos extras vem de um plano de rotação ligado ao identificador da sessão (`site/lib/assign.php`; pormenor em `assignment_plan.md`). Depois do mínimo, o catálogo restante pode ser desbloqueado.

## Geração (resumo)

Quatro âncoras Hugging Face: E1 `microsoft/DialoGPT-medium`; E2 `facebook/blenderbot-400M-distill`; E3 `microsoft/Phi-3-mini-4k-instruct`; E4 `Qwen/Qwen2.5-3B-Instruct`. Semente 42, \(\tau = 0{,}10\). IDs e lote em `pipeline/pipeline.py` e `data/all_results.json`. Células inválidas foram geradas de novo na mesma célula até uma resposta aceite; o número de regenerações **não** ficou no log. O lote avaliado são as 96 células finais. Regenerar células **não** reproduz a avaliação humana já recolhida.
