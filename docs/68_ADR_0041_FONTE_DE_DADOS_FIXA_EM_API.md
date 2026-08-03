# ADR-0041 | Fonte de dados fixa em API (nuvem) - sem seleção visível, botão de sincronizar

## Contexto

Pedido do responsável do produto: "os arquivos sempre virão da API
(Nuvem)" - o seletor "Fonte de dados" (Arquivo local / API), a URL do
backend e o token de sincronização não deveriam mais aparecer na tela.
Pediu um botão de sincronização no canto superior direito (ou
automático, se não precisar de botão).

## Decisão

### 1. Escopo real - só 2 das 5 telas tinham esse seletor

Conferido em todas as telas do painel: só `painel/telas/dashboard.py`
("Visão geral") e `painel/telas/falhas.py` ("Falhas") tinham o
seletor "Arquivo local" / "API (nuvem)" - a captura de tela do
responsável do produto era da "Visão geral", mas o mesmo padrão estava
duplicado em "Falhas" também, então apliquei a mudança nas duas por
consistência (senão uma aba ficaria "limpa" e a outra continuaria
pedindo fonte/URL/token).

`painel/telas/mapa_operacional.py`, `capacidade_pcm.py` e
`dados_exportacoes.py` **não têm** esse seletor - são só arquivo local
(sem opção de API nenhuma hoje). Não mexidas nesta ADR - ver
`docs/69_ADR_0042_*` (levantamento do que falta pra geolocalização),
que trata isso como uma lacuna de arquitetura, não um ajuste de UI.

### 2. Fonte fixa em API, credenciais só via `st.secrets`

`dashboard.py`/`falhas.py`: removido o `st.radio` de fonte, os
`st.text_input` de URL/token, e o branch inteiro de "Arquivo local"
(incluindo os botões "Gerar dados de exemplo" e o "Simulador de dados
ETL" - ver seção 4). URL e token agora vêm exclusivamente de
`st.secrets["SYNC_API_URL"]`/`st.secrets["SYNC_TOKEN"]` - nunca mais
digitados na tela. Se os secrets não estiverem configurados, a tela
mostra `st.error` orientando a configurar no Streamlit Cloud (Settings
→ Secrets) e para (`st.stop()`), em vez de pedir pro usuário digitar.

### 3. "Sincronizar dados" é mais reafirmação do que necessidade técnica

`carregar_jornadas_via_api` não tem cache (`st.cache_data`) - toda
interação no painel (mudar um filtro, clicar em qualquer botão) já
dispara um rerun completo do Streamlit, que já busca os dados de novo
no backend. Ou seja: o painel **já era automático** nesse sentido antes
mesmo deste ADR. O botão "🔄 Sincronizar dados" (canto superior
direito, ao lado do título, via `st.columns([5, 1])`) existe como
afirmação visual explícita pro usuário ("acabei de atualizar"), com um
`st.toast` de feedback - não muda o comportamento técnico, só dá a
sensação de controle que foi pedida. Se no futuro os dados crescerem a
ponto de precisar de cache, o botão vira o lugar natural pra limpar
esse cache (`st.cache_data.clear()`).

### 4. Efeito colateral: botão de dados de exemplo e simulador ETL saíram da UI

O botão "Gerar dados de exemplo (teste)" e o expander "Simulador de
dados (ETL)" (ADR-0033) só faziam sentido no modo "Arquivo local" -
escreviam jornadas fabricadas num diretório local pra depois carregar
de volta. Com esse modo removido da UI, os dois pararam de aparecer no
painel publicado. As funções (`gerar_jornadas_exemplo`,
`gerar_jornadas_exemplo_volumoso` em `painel/dados.py`) continuam no
código, testadas por `pytest`, e continuam úteis pra rodar localmente
durante desenvolvimento (como já foram usadas nesta mesma sessão) -
só não têm mais um botão na tela publicada.

### 5. Testes de ponta a ponta atualizados (e um novo)

`tests/test_falhas_painel.py` (`AppTest`, executa o script real)
dependia do fluxo "Arquivo local" - reescrito pra simular API via
`AppTest.secrets` (`SYNC_API_URL`/`SYNC_TOKEN`) e substituir
`dados.carregar_jornadas_via_api` por uma versão falsa via
`monkeypatch` (não há backend real disponível no teste). Ganhou um
terceiro teste (`sem_secrets_mostra_erro_sem_quebrar`) cobrindo o caso
novo de secrets ausentes.

`tests/test_dashboard_painel.py` (novo) - mesmo padrão de `AppTest`
aplicado à "Visão geral", que não tinha essa camada de teste de ponta
a ponta antes (só `test_painel.py`, que testa `dados.py`/`graficos.py`
sem Streamlit). Cobre a mesma mudança estrutural de fonte de dados,
que é justamente o tipo de risco (import/session_state/ordem dos
widgets) que só aparece rodando o script inteiro.

## Validação de qualidade realizada

- `python -m py_compile` em `painel/telas/dashboard.py`,
  `painel/telas/falhas.py`, `tests/test_falhas_painel.py`,
  `tests/test_dashboard_painel.py`: OK.
- `pytest` completo: 304 passed (298 anteriores - 2 reescritos + 3
  novos em `test_falhas_painel.py`, + 3 novos em
  `test_dashboard_painel.py`), sem regressão.
- Smoke test real do `streamlit run painel/app.py`: HTTP 200, sem
  traceback no log.

## Validação NÃO realizada

- Teste visual em navegador real (alinhamento do botão "Sincronizar
  dados" com o título, toast aparecendo) - sandbox sem Playwright/
  Chromium, mesma limitação de sempre. Desta vez, porém, o
  comportamento **funcional** (fluxo de dados, mensagens de erro/info,
  ausência de exceção) foi validado de ponta a ponta via `AppTest` -
  risco bem menor que os ajustes de CSS puro das ADRs anteriores.

## Arquivos afetados

- `painel/telas/dashboard.py`, `painel/telas/falhas.py` (seletor de
  fonte/URL/token removido, botão de sincronizar adicionado).
- `tests/test_falhas_painel.py` (reescrito pra simular API).
- `tests/test_dashboard_painel.py` (novo).
