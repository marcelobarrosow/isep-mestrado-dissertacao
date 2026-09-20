# Codebook — classificações públicas

Ficheiro: `classificacoes_publicas.csv` (UTF-8, cabeçalhos em português europeu).

Uma linha = uma classificação de um item (célula estímulo × época × condição) por um participante. Não há demografia nem texto livre do participante. Os identificadores internos de sessão foram substituídos por IDs opacos (`P001`…`P156`), na ordem numérica dos IDs originais.

## Colunas

| Coluna | Conteúdo |
|---|---|
| `participante` | ID opaco da sessão (`P001`–`P156`). |
| `idioma` | Língua da interface (`Português` / `Inglês`). |
| `estado` | Estado da sessão (`concluído`, `em curso`, …). |
| `atenção` | Verificação de atenção (`Sim` / `Não`). |
| `motivo de exclusão` | Vazio, `ritmo demasiado rápido` ou `falha no item de atenção`. |
| `código do item` | Identificador estável da célula (`sXX__EY__condition`). |
| `classificação` | Nota Likert de empatia percebida (1–7). |
| `ordem` | Posição do item na sequência da sessão. |
| `estímulo` | Identificador do enunciado (`s01`–`s12`). |
| `época` | Factor experimental (`E1`–`E4`). |
| `condição` | `linha de base` ou `pipeline`. |
| `modelo` | Identificador Hugging Face do gerador âncora. |
| `tempo da resposta (s)` | Intervalo entre itens consecutivos (ver abaixo). |
| `mediana do item (s)` | Mediana do tempo desse item na exportação. |
| `ritmo relativo` | Tempo do participante / mediana do item. |
| `ritmo demasiado rápido` | Indicador calculado na exportação (limiar mediana − 2,5 × DAM). |

## Colunas removidas

Não entram no ficheiro público: `início`, `conclusão`, `última actualização`, `respondido em` (marcas temporais absolutas). Essas colunas existem na exportação arquivada na dissertação (`appendices/data/exportacao_questionario_*.csv`). Também não há tokens de retoma nem dados de administração.

## Ritmo versus duração de sessão

O filtro de ritmo demasiado rápido usa os tempos das *respostas* (`tempo da resposta (s)` e colunas derivadas), não a duração da sessão.

## Filtro estrito da dissertação

A análise principal retém linhas com item e classificação, `estado = concluído`, `atenção = Sim`, e sem motivo de exclusão `ritmo demasiado rápido` ou `falha no item de atenção`. Ver `pipeline/analyze_survey_mixed.py` e `pipeline/analyze_survey_export.py`.
