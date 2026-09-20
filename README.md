# Ambivalência e empatia percebida em chatbots

Repositório de replicação da dissertação *Sinal de Ambivalência Emocional em Texto e Empatia Percebida em Chatbots* (TMDEI / ISEP).

Endereço: <https://github.com/marcelobarrosow/ambivalence-empathy-chatbots>

Este pacote contém as fontes LaTeX, o código de geração e de análise, o instrumento do questionário (sem credenciais) e os artefactos canónicos usados na dissertação. **Não** inclui a base operacional (tokens de retoma, palavra-passe de administração, dumps MariaDB). O ficheiro de classificações não tem demografia nem texto livre do participante: só classificações Likert e metadados de célula necessários à replicação.

O protocolo do estudo (fluxo PHP, funil 156 / 63 / 52, rotação, exclusões) está em `pipeline/questionnaire/protocolo.md`.

## Pastas

- `documento/` — fontes LaTeX da dissertação (`main.tex`, `ch1/`–`ch6/`, `frontmatter/`, `appendices/`, `mainbibliography.bib`, estilo TMDEI). A capa oficial A4 está em `documento/frontmatter/assets/`. O PDF submetido no Requerimento **não** vai para o GitHub; regenera-se localmente (secção abaixo). Os JSON/CSV em `documento/appendices/data/` são cópias de arquivo citadas no texto; o LaTeX não os lê. O Apêndice B já está em `appendixB.tex`.
- `pipeline/` — geração (`pipeline.py`, `emotion_analyzer.py`, `prompts.py`, `generator.py`, `quality.py`, `cells.py`), análise (`analyze_survey_export.py`, `analyze_survey_mixed.py`), sincronização de artefactos (`sync_study_artifacts.py`) e *shell* de QA. Testes sem GPU, a partir de `pipeline/`: `python -m unittest discover -s tests`. O protocolo e o plano de afetação estão em `pipeline/questionnaire/`.
- `site/` — questionário PHP/MariaDB (`index.php`, `consent.php`, `survey.php`, `admin/`, `sql/schema.sql`, `lang/pt.php` e `lang/en.php`). Copiar `config.example.php` para `config.local.php` no servidor; não commitar passwords. Não há passo demográfico.
- `data/` — artefactos canónicos da replicação: estímulos (`stimuli.json`), 96 células (`all_results.json`, `questionnaire_items*.csv`), modelo misto arquivado (`mixed_crossed_strict.json`), classificações públicas (`classificacoes_publicas.csv`) e `codebook.md`. `pipeline/stimuli.json` e `site/data/questionnaire_items_i18n.csv` são cópias de trabalho alinhadas com esta pasta.

## O que não entra

- `.env`, passwords, tokens de retoma
- dumps da base operacional
- pesos locais de modelos Hugging Face
- timestamps absolutos de sessão ou de item
- auxiliares LaTeX (`documento/build/`) e o `documento/main.pdf` gerado

## Como regenerar o PDF

Na pasta `documento/` é preciso TeX Live (ou equivalente) com `pdflatex`, `biber`, `makeglossaries` e `latexmk`.

```bash
cd documento
latexmk -pdf main.tex
```

Em Linux e macOS também serve `make`. O PDF fica em `documento/build/main.pdf` e é copiado para `documento/main.pdf`. Os auxiliares ficam em `documento/build/` e estão no `.gitignore`.

## Como repetir a análise (pasta limpa)

A inferência principal da dissertação é o modelo misto linear com efeitos aleatórios cruzados (participante × item), filtro estrito.

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r pipeline/requirements-analysis.txt
python pipeline/analyze_survey_mixed.py data/classificacoes_publicas.csv --json mixed_replicated.json
python pipeline/analyze_survey_export.py data/classificacoes_publicas.csv --filter estrito
```

Os cabeçalhos e valores categóricos estão em português (`participante`, `código do item`, `classificação`, `atenção`, `estado`, `motivo de exclusão`, `época`, `condição`). A coluna `participante` neste CSV já é o ID opaco (`P001`…). Ver `data/codebook.md`.

O resultado arquivado da corrida da dissertação está em `data/mixed_crossed_strict.json`.

## Lote canónico e geração opcional

O lote avaliado está em `data/all_results.json` (96 células). Células vazias ou inválidas foram geradas de novo na mesma célula até obter uma resposta aceite. O número de regenerações **não** ficou no log.

`pipeline.py` escreve células novas em `pipeline/outputs/` (rascunho). Isso **não** substitui o lote canónico em `data/`. Regenerar **não** reproduz a avaliação humana já recolhida. A temperatura no código actual é nula (DialoGPT: *beam search* 5); o JSON arquivado mistura `null` e `0.4` (tabela de geração da dissertação).

Para voltar a gerar células, `pipeline/requirements.txt` instala Transformers/PyTorch. As âncoras são as da dissertação: DialoGPT-medium (E1), BlenderBot-400M-distill (E2), Phi-3-mini-Instruct (E3), Qwen2.5-3B-Instruct (E4). IDs em `pipeline/pipeline.py` e `data/all_results.json`. Sem APIs proprietárias.

`sync_study_artifacts.py` lê `data/all_results.json` e, por omissão, actualiza CSVs e o Apêndice B em `documento/`. Use `--skip-latex` se não quiser tocar nas fontes LaTeX.

O CLI de geração é `pipeline/pipeline.py` (reexporta os símbolos que os *shells* importam). A lógica está em:

- `emotion_analyzer.py` — GoEmotions em CPU e derivação de ambivalência (`τ=0.10`)
- `prompts.py` — *prompts* baseline e pipeline por arquitectura (`causal_dialogue`, `seq2seq`, `chat`)
- `generator.py` — `HFGenerator` das âncoras E1–E4
- `quality.py` — heurísticas de QA da resposta
- `cells.py` — `run_cell`, persistência, *merge* e CSV cego (`item_001`…; os IDs canónicos `sXX__EY__condition` vêm de `sync_study_artifacts.py`)
- `goemotions.py` — CLI fino sobre `EmotionAnalyzer`

## Consentimento e dados

O estudo não recolheu demografia. Este repositório publica classificações Likert anonimizadas e artefactos de geração para replicação estatística, sem texto livre do participante. As classificações anonimizadas e os artefactos de geração ficam neste repositório público por tempo indeterminado.
