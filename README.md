# Ambivalência e empatia percebida em chatbots

Dissertação de mestrado de Marcelo Mota Barroso, no [TMDEI](https://www.dei.isep.ipp.pt) do [ISEP](https://www.isep.ipp.pt) (Engenharia de Software), orientada pelo Dr. Constantino Martins.

O trabalho pergunta se vale a pena dizer explicitamente a um chatbot que o enunciado do utilizador é emocionalmente ambivalente — alegria e medo no mesmo texto, por exemplo — para que a resposta pareça mais empática. Compara-se a mesma geração com e sem esse sinal, em quatro modelos públicos de épocas diferentes (DialoGPT, BlenderBot, Phi-3-mini-Instruct e Qwen2.5-3B-Instruct). Pessoas avaliaram as respostas sem saber qual o modelo nem se o sinal estava presente. Nesta amostra, o sinal não mostrou um ganho claro; o que mais mudou a nota de empatia foi o gerador usado.

Este repositório junta o texto da dissertação, o código que gerou as respostas, o questionário online e as classificações já anonimizadas, para quem quiser ler o estudo, recompilar o PDF ou repetir a análise. Repositório: <https://github.com/marcelobarrosow/isep-mestrado-dissertacao>.

Como correu o questionário (consentimento, ordem dos itens, quem entrou na análise) está descrito em [`pipeline/questionnaire/protocolo.md`](pipeline/questionnaire/protocolo.md).

## O que está neste repositório

- [`documento/`](documento/) — fontes LaTeX da dissertação. O ficheiro principal é [`main.tex`](documento/main.tex); os capítulos estão em [`ch1/`](documento/ch1/) a [`ch6/`](documento/ch6/); a capa, o resumo e o glossário em [`frontmatter/`](documento/frontmatter/); os apêndices em [`appendices/`](documento/appendices/); a bibliografia em [`mainbibliography.bib`](documento/mainbibliography.bib). A capa oficial A4 está em [`capa-oficial-isep-frente-A4.pdf`](documento/frontmatter/assets/capa-oficial-isep-frente-A4.pdf). O PDF final não é publicado aqui: gera-se no computador (secção seguinte). As 96 respostas avaliadas no Apêndice B já estão em [`appendixB.tex`](documento/appendices/appendixB.tex).
- [`pipeline/`](pipeline/) — código Python. Gera as respostas dos quatro modelos ([`pipeline.py`](pipeline/pipeline.py), [`emotion_analyzer.py`](pipeline/emotion_analyzer.py), [`prompts.py`](pipeline/prompts.py), [`generator.py`](pipeline/generator.py), [`quality.py`](pipeline/quality.py), [`cells.py`](pipeline/cells.py)) e estima as estatísticas a partir do CSV público ([`analyze_survey_mixed.py`](pipeline/analyze_survey_mixed.py), [`analyze_survey_export.py`](pipeline/analyze_survey_export.py)). [`sync_study_artifacts.py`](pipeline/sync_study_artifacts.py) actualiza os CSVs e o Apêndice B a partir do lote de respostas. Testes sem GPU, a partir da pasta `pipeline/`: `python -m unittest discover -s tests`. O desenho do questionário está em [`protocolo.md`](pipeline/questionnaire/protocolo.md) e [`assignment_plan.md`](pipeline/questionnaire/assignment_plan.md).
- [`site/`](site/) — o questionário que os participantes usaram (PHP e MariaDB): entrada em [`index.php`](site/index.php), consentimento em [`consent.php`](site/consent.php), itens em [`survey.php`](site/survey.php), painel em [`admin/`](site/admin/), esquema da base em [`schema.sql`](site/sql/schema.sql), textos em [`pt.php`](site/lang/pt.php) e [`en.php`](site/lang/en.php). Num servidor, copia-se [`config.example.php`](site/config.example.php) para `config.local.php` e preenchem-se as credenciais localmente, sem as enviar para o GitHub. Não se pediu idade, sexo nem outras variáveis demográficas.
- [`data/`](data/) — os ficheiros para repetir a análise: os 12 enunciados em [`stimuli.json`](data/stimuli.json), as 96 respostas geradas em [`all_results.json`](data/all_results.json), o catálogo do questionário em [`questionnaire_items.csv`](data/questionnaire_items.csv) e [`questionnaire_items_i18n.csv`](data/questionnaire_items_i18n.csv), o modelo misto gravado em [`mixed_crossed_strict.json`](data/mixed_crossed_strict.json), as notas Likert anonimizadas em [`classificacoes_publicas.csv`](data/classificacoes_publicas.csv) e a explicação das colunas em [`codebook.md`](data/codebook.md). [`pipeline/stimuli.json`](pipeline/stimuli.json) e [`site/data/questionnaire_items_i18n.csv`](site/data/questionnaire_items_i18n.csv) são cópias de trabalho iguais a estes.

## Como gerar o PDF da dissertação

Na pasta [`documento/`](documento/) instale TeX Live (ou equivalente) com `pdflatex`, `biber`, `makeglossaries` e `latexmk`. Depois:

```bash
cd documento
latexmk -pdf main.tex
```

Em Linux e macOS também serve [`make`](documento/Makefile). O PDF aparece em `documento/build/main.pdf` e é copiado para `documento/main.pdf`. Os ficheiros auxiliares da compilação ficam em `documento/build/` e não são versionados ([`.gitignore`](.gitignore)).

## Como repetir a análise estatística

A análise principal da dissertação é um modelo linear misto: cada nota Likert pertence ao mesmo tempo a um participante e a um item, por isso esses dois factores entram como efeitos aleatórios cruzados. Usa-se o filtro estrito (atenção correcta e ritmo não demasiado rápido): 52 pessoas e 2016 classificações.

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r pipeline/requirements-analysis.txt
python pipeline/analyze_survey_mixed.py data/classificacoes_publicas.csv --json mixed_replicated.json
python pipeline/analyze_survey_export.py data/classificacoes_publicas.csv --filter estrito
```

Os nomes das colunas no CSV estão em português. O identificador `participante` já é opaco (`P001`, `P002`, …). O significado de cada coluna está em [`data/codebook.md`](data/codebook.md). O resultado que a dissertação reporta está em [`data/mixed_crossed_strict.json`](data/mixed_crossed_strict.json). As bibliotecas Python desta análise estão em [`pipeline/requirements-analysis.txt`](pipeline/requirements-analysis.txt).

## Como voltar a gerar as respostas dos modelos (opcional)

As 96 respostas que as pessoas avaliaram estão em [`data/all_results.json`](data/all_results.json). Se uma célula saía vazia ou inválida, gerava-se outra vez na mesma célula até ser aceite. Quantas vezes isso aconteceu **não** ficou registado.

Correr [`pipeline.py`](pipeline/pipeline.py) de novo escreve rascunhos em `pipeline/outputs/`. Isso não substitui o ficheiro em [`data/`](data/) e **não** reproduz as notas humanas já recolhidas. No código actual a temperatura é nula (no DialoGPT usa-se *beam search* com 5 feixes). O JSON arquivado ainda mistura `null` e `0.4` nalguns campos; a tabela da dissertação é que descreve o protocolo.

Para gerar de novo precisa de GPU ou de uma máquina capaz de carregar os modelos. Instale [`pipeline/requirements.txt`](pipeline/requirements.txt) (Transformers e PyTorch). Os quatro modelos são públicos no Hugging Face: DialoGPT-medium (E1), BlenderBot-400M-distill (E2), Phi-3-mini-Instruct (E3) e Qwen2.5-3B-Instruct (E4). Os identificadores exactos estão em [`pipeline.py`](pipeline/pipeline.py) e em [`all_results.json`](data/all_results.json). Não se usam APIs pagas.

[`sync_study_artifacts.py`](pipeline/sync_study_artifacts.py) lê [`all_results.json`](data/all_results.json) e, por omissão, actualiza os CSVs e [`appendixB.tex`](documento/appendices/appendixB.tex). Passe `--skip-latex` se só quiser actualizar os CSVs.

O ponto de entrada da geração é [`pipeline.py`](pipeline/pipeline.py). Por dentro:

- [`emotion_analyzer.py`](pipeline/emotion_analyzer.py) — classificador GoEmotions em CPU e regra de ambivalência (`τ = 0,10`)
- [`prompts.py`](pipeline/prompts.py) — textos enviados a cada arquitectura (`causal_dialogue`, `seq2seq`, `chat`)
- [`generator.py`](pipeline/generator.py) — chamada aos quatro modelos
- [`quality.py`](pipeline/quality.py) — regras que rejeitam uma resposta mal formada
- [`cells.py`](pipeline/cells.py) — uma célula = um estímulo × uma época × uma condição
- [`goemotions.py`](pipeline/goemotions.py) — atalho de linha de comando para o classificador

## Dados pessoais e consentimento

Não se recolheu demografia. O que está público são notas Likert já anonimizadas e as respostas geradas pelos modelos, sem texto livre escrito pelos participantes. As notas estão em [`classificacoes_publicas.csv`](data/classificacoes_publicas.csv). O texto de consentimento que as pessoas leram está em [`site/lang/pt.php`](site/lang/pt.php) e [`site/lang/en.php`](site/lang/en.php). Estes ficheiros ficam neste repositório público.

---

# Emotional ambivalence and perceived empathy in chatbots

Master’s dissertation by Marcelo Mota Barroso, in [TMDEI](https://www.dei.isep.ipp.pt) at [ISEP](https://www.isep.ipp.pt) (Software Engineering), supervised by Dr Constantino Martins.

The study asks whether it is worth telling a chatbot, explicitly, that the user’s utterance is emotionally ambivalent — joy and fear in the same sentence, for example — so that the reply feels more empathic. It compares the same generation with and without that signal, on four public models from different periods (DialoGPT, BlenderBot, Phi-3-mini-Instruct and Qwen2.5-3B-Instruct). People rated the replies without knowing which model produced them or whether the signal was present. In this sample the signal did not show a clear gain; perceived empathy varied much more across generators than between the two conditions.

This repository holds the dissertation source, the code that produced the replies, the online questionnaire, and the already anonymised ratings, so that someone can read the study, rebuild the PDF or rerun the analysis. Repository: <https://github.com/marcelobarrosow/isep-mestrado-dissertacao>.

How the questionnaire ran (consent, item order, who entered the analysis) is described in [`pipeline/questionnaire/protocolo.md`](pipeline/questionnaire/protocolo.md).

## What is in this repository

- [`documento/`](documento/) — LaTeX sources for the dissertation. The main file is [`main.tex`](documento/main.tex); chapters are in [`ch1/`](documento/ch1/) to [`ch6/`](documento/ch6/); cover, abstract and glossary in [`frontmatter/`](documento/frontmatter/); appendices in [`appendices/`](documento/appendices/); bibliography in [`mainbibliography.bib`](documento/mainbibliography.bib). The official A4 cover is [`capa-oficial-isep-frente-A4.pdf`](documento/frontmatter/assets/capa-oficial-isep-frente-A4.pdf). The finished PDF is not published here: you build it locally (next section). The 96 rated replies in Appendix B are already in [`appendixB.tex`](documento/appendices/appendixB.tex).
- [`pipeline/`](pipeline/) — Python code. It generates replies from the four models ([`pipeline.py`](pipeline/pipeline.py), [`emotion_analyzer.py`](pipeline/emotion_analyzer.py), [`prompts.py`](pipeline/prompts.py), [`generator.py`](pipeline/generator.py), [`quality.py`](pipeline/quality.py), [`cells.py`](pipeline/cells.py)) and estimates the statistics from the public CSV ([`analyze_survey_mixed.py`](pipeline/analyze_survey_mixed.py), [`analyze_survey_export.py`](pipeline/analyze_survey_export.py)). [`sync_study_artifacts.py`](pipeline/sync_study_artifacts.py) refreshes the CSVs and Appendix B from the reply batch. Tests without a GPU, from the `pipeline/` folder: `python -m unittest discover -s tests`. The questionnaire design is in [`protocolo.md`](pipeline/questionnaire/protocolo.md) and [`assignment_plan.md`](pipeline/questionnaire/assignment_plan.md).
- [`site/`](site/) — the questionnaire participants used (PHP and MariaDB): entry at [`index.php`](site/index.php), consent at [`consent.php`](site/consent.php), items at [`survey.php`](site/survey.php), admin panel in [`admin/`](site/admin/), database schema in [`schema.sql`](site/sql/schema.sql), copy in [`pt.php`](site/lang/pt.php) and [`en.php`](site/lang/en.php). On a server, copy [`config.example.php`](site/config.example.php) to `config.local.php` and fill in credentials locally; do not push them to GitHub. Age, sex and other demographics were not collected.
- [`data/`](data/) — files needed to rerun the analysis: the 12 prompts in [`stimuli.json`](data/stimuli.json), the 96 generated replies in [`all_results.json`](data/all_results.json), the questionnaire catalogue in [`questionnaire_items.csv`](data/questionnaire_items.csv) and [`questionnaire_items_i18n.csv`](data/questionnaire_items_i18n.csv), the saved mixed model in [`mixed_crossed_strict.json`](data/mixed_crossed_strict.json), the anonymised Likert scores in [`classificacoes_publicas.csv`](data/classificacoes_publicas.csv), and the column descriptions in [`codebook.md`](data/codebook.md). [`pipeline/stimuli.json`](pipeline/stimuli.json) and [`site/data/questionnaire_items_i18n.csv`](site/data/questionnaire_items_i18n.csv) are working copies of the same files.

## How to build the dissertation PDF

In [`documento/`](documento/) install TeX Live (or equivalent) with `pdflatex`, `biber`, `makeglossaries` and `latexmk`. Then:

```bash
cd documento
latexmk -pdf main.tex
```

On Linux and macOS [`make`](documento/Makefile) also works. The PDF appears at `documento/build/main.pdf` and is copied to `documento/main.pdf`. Auxiliary compilation files stay in `documento/build/` and are not versioned ([`.gitignore`](.gitignore)).

## How to rerun the statistical analysis

The dissertation’s main analysis is a linear mixed model: each Likert rating belongs to both a participant and an item, so those two factors enter as crossed random effects. It uses the strict filter (correct attention check and not too fast a pace): 52 people and 2,016 ratings.

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r pipeline/requirements-analysis.txt
python pipeline/analyze_survey_mixed.py data/classificacoes_publicas.csv --json mixed_replicated.json
python pipeline/analyze_survey_export.py data/classificacoes_publicas.csv --filter estrito
```

Column names in the CSV are in Portuguese. The `participante` identifier is already opaque (`P001`, `P002`, …). What each column means is in [`data/codebook.md`](data/codebook.md). The result reported in the dissertation is in [`data/mixed_crossed_strict.json`](data/mixed_crossed_strict.json). Python libraries for this analysis are in [`pipeline/requirements-analysis.txt`](pipeline/requirements-analysis.txt).

## How to regenerate model replies (optional)

The 96 replies people rated are in [`data/all_results.json`](data/all_results.json). If a cell came out empty or invalid, it was generated again in the same cell until one was accepted. How many times that happened was **not** logged.

Running [`pipeline.py`](pipeline/pipeline.py) again writes drafts to `pipeline/outputs/`. That does not replace the file in [`data/`](data/) and **does not** reproduce the human ratings already collected. In the current code temperature is zero (DialoGPT uses beam search with 5 beams). The archived JSON still mixes `null` and `0.4` in some fields; the dissertation table is the protocol.

Generating again needs a GPU or a machine that can load the models. Install [`pipeline/requirements.txt`](pipeline/requirements.txt) (Transformers and PyTorch). The four models are public on Hugging Face: DialoGPT-medium (E1), BlenderBot-400M-distill (E2), Phi-3-mini-Instruct (E3) and Qwen2.5-3B-Instruct (E4). Exact identifiers are in [`pipeline.py`](pipeline/pipeline.py) and [`all_results.json`](data/all_results.json). No paid APIs are used.

[`sync_study_artifacts.py`](pipeline/sync_study_artifacts.py) reads [`all_results.json`](data/all_results.json) and, by default, updates the CSVs and [`appendixB.tex`](documento/appendices/appendixB.tex). Pass `--skip-latex` if you only want to refresh the CSVs.

The generation entry point is [`pipeline.py`](pipeline/pipeline.py). Inside:

- [`emotion_analyzer.py`](pipeline/emotion_analyzer.py) — GoEmotions classifier on CPU and the ambivalence rule (`τ = 0.10`)
- [`prompts.py`](pipeline/prompts.py) — text sent to each architecture (`causal_dialogue`, `seq2seq`, `chat`)
- [`generator.py`](pipeline/generator.py) — calls to the four models
- [`quality.py`](pipeline/quality.py) — rules that reject a malformed reply
- [`cells.py`](pipeline/cells.py) — one cell = one prompt × one epoch × one condition
- [`goemotions.py`](pipeline/goemotions.py) — command-line shortcut for the classifier

## Personal data and consent

No demographics were collected. What is public are already anonymised Likert scores and the model-generated replies, with no free-text written by participants. The scores are in [`classificacoes_publicas.csv`](data/classificacoes_publicas.csv). The consent text people read is in [`site/lang/pt.php`](site/lang/pt.php) and [`site/lang/en.php`](site/lang/en.php). These files remain in this public repository.
