# Plano de rotação (identificador da sessão)

Total de células: 96 (`12 estímulos × 4 épocas × 2 condições`). Implementação: `site/lib/assign.php`. O fluxo da sessão está em `protocolo.md`.

A ordem do bloco mínimo e dos extras vem de um plano de rotação ligado ao identificador da sessão.

## Objectivo

Cada sessão avalia um bloco mínimo de ~24 itens; o conjunto das sessões cobre o catálogo com sobreposição. Depois do mínimo, o participante pode desbloquear o restante (`continue_offer.php`), **antes** da verificação de atenção.

## Implementação

As 96 linhas do catálogo são baralhadas com semente 42 e partidas em 8 blocos de 12 itens. Cada sessão recebe dois blocos segundo o plano em `assign.php` (índice da sessão, **módulo** o comprimento do plano).

O plano abaixo tem 15 combinações. Isso é o comprimento do ciclo de rotação, não o tamanho da amostra. A amostra do estudo: iniciaram 156, concluíram 63, o filtro estrito retém 52.

| Índice no ciclo (módulo 15) | Blocos (12+12 ≈ 24 itens) |
|---|---|
| 1 | B1 + B2 |
| 2 | B2 + B3 |
| 3 | B3 + B4 |
| 4 | B4 + B5 |
| 5 | B5 + B6 |
| 6 | B6 + B7 |
| 7 | B7 + B8 |
| 8 | B8 + B1 |
| 9 | B1 + B3 |
| 10 | B2 + B4 |
| 11 | B5 + B7 |
| 12 | B6 + B8 |
| 13 | B1 + B5 |
| 14 | B2 + B6 |
| 15 | B3 + B7 |

Ordem dos 24 itens do núcleo: aleatorizar por sessão (`seed = 42 + id` do participante). Os extras, se desbloqueados na oferta pós-mínimo, são o resto do catálogo, baralhado com `seed = 9000 + id`.

O instrumento é o questionário PHP/MariaDB deste repositório.
