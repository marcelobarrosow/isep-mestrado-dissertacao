# Ambivalence and perceived empathy in chatbots

Repositório de replicação da dissertação *Análise de Emoções Ambivalentes em Texto para Melhoria da Empatia em Chatbots* (TMDEI / ISEP).

Endereço previsto: <https://github.com/marcelobarrosow/ambivalence-empathy-chatbots>

Este directório é o contrato do que entra no GitHub público. O *push* faz-se depois de copiar para aqui o código e os artefactos listados abaixo. **Não** publicar a base operacional do questionário (tokens de retoma, palavra-passe de administração, dumps MariaDB).

## O que deve ficar neste repositório

- `pipeline.py` e adaptadores dos quatro geradores âncora
- `requirements.txt`
- `site/` do questionário (schema SQL, exportação), sem credenciais
- `sync_study_artifacts.py`
- `analyze_survey_export.py`
- `analyze_survey_mixed.py`
- artefactos canónicos (já na dissertação, em `tmdei-dissertation-template-main-4/appendices/data/`):
  - `questionnaire_items.csv`
  - `questionnaire_items_i18n.csv`
  - `all_results.json`
  - `stimuli.json`
  - `mixed_crossed_strict.json`
  - export do questionário **anonimizado** (sem tokens de sessão)

## O que não entra

- `.env`, passwords, tokens de retoma
- dumps da base operacional
- pesos locais de modelos Hugging Face

## Como repetir a análise

1. Instalar dependências com `requirements.txt`.
2. Os 96 itens avaliados estão em `questionnaire_items.csv` / `all_results.json`.
3. A análise principal lê o export anonimizado e produz o misto cruzado (`analyze_survey_mixed.py`).
