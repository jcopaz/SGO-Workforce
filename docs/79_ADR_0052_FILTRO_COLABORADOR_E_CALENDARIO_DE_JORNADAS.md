# ADR-0052 | Filtro Colaborador separado + calendário de dias com jornada no mapa operacional

## Contexto

Feedback do responsável pelo produto em 2026-08-04, olhando o filtro
"Jornada" do mapa operacional (um único `st.selectbox` combinando
matrícula e horário de início no mesmo rótulo, ex.: "30027171 -
04/08/2026 17:39:12"): separar em dois campos - "Colaborador" e
"Jornada" lado a lado - e, ao lado, um calendário que ao ser aberto
mostra os dias com apontamento/captura de pulso marcados (pontos
vermelhos ou sombreado), para escolher visualmente o dia antes de
selecionar a jornada.

## Decisão

### 1. Colaborador e Jornada separados

Novo `st.selectbox` "Colaborador" (lista de matrículas únicas entre as
jornadas carregadas). "Jornada" passa a listar só as jornadas *daquele*
colaborador (mais recente primeiro), com rótulo só a data/hora de
início (a matrícula já está no campo ao lado, não precisa repetir).
`_sanitizar_selectbox_state` (mesmo padrão de
`_sanitizar_multiselect_state`/`_sanitizar_selectbox_state` já usados em
`dashboard.py`) evita `StreamlitAPIException` quando trocar de
colaborador muda a lista de jornadas disponíveis.

### 2. Calendário de dias com jornada

Pesquisa confirmou que **`st.date_input` nativo do Streamlit não suporta
marcar datas específicas** (há um pedido em aberto no próprio repositório
do Streamlit pedindo exatamente isso, sem previsão). Duas alternativas de
componente de terceiro foram avaliadas:

- `streamlit-calendar` (baseado no FullCalendar.js) - biblioteca JS
  madura por trás, mas pacote genérico/pesado para o caso de uso (visão
  de calendário completa com eventos, não "marcar dia disponível").
- `streamlit-calendar-input` - API mínima e exata para o pedido:
  `calendar_input(available_dates) -> Optional[datetime]`, grid de mês
  sempre visível (não um dropdown que abre ao clicar - confirmado lendo
  o CSS/JS do próprio pacote antes de integrar), verde para dia
  disponível, vermelho para indisponível, cinza para dia de
  preenchimento fora do mês.

**Risco assumido conscientemente**: `streamlit-calendar-input` é um
pacote pequeno e pouco maduro (2 estrelas no GitHub, mantido por uma
pessoa, sem suíte de teste automatizado visível, versão `0.0.3`).
Apresentado esse risco explicitamente ao responsável pelo produto, que
confirmou querer testar mesmo assim. Mitigação: versão **fixada**
(`==0.0.3`, não uma faixa) em `requirements.txt`, para uma atualização
do pacote nunca quebrar o painel sem passar por uma decisão explícita
de subir a versão.

### 3. Integração (`painel/telas/mapa_operacional.py`)

`datas_com_jornada` = datas (horário de Brasília) das jornadas do
colaborador selecionado. Calendário renderizado ao lado do seletor de
Colaborador (`st.columns([1, 2])`, já que o grid de mês precisa de mais
espaço horizontal). Chave do componente inclui o colaborador
(`f"painel_mapa_calendario_{colaborador_selecionado}"`) - evita
reaproveitar um dia clicado de outra pessoa que pode nem existir na
lista de dias disponíveis do colaborador atual.

Clicar num dia verde restringe a lista de "Jornada" abaixo às jornadas
daquele colaborador que começaram naquele dia (normalmente 1, mas o
motor de domínio não impede tecnicamente mais de uma no mesmo dia
calendário). **Sem clicar em nada**, "Jornada" continua mostrando todas
as jornadas do colaborador, como já era antes - a tela nunca fica
travada esperando uma interação com o componente novo.

## Validação de qualidade realizada

- `python -m py_compile`: OK.
- `pytest` completo: 369 passed, sem regressão (nenhum teste novo -
  a integração em si é orquestração de Streamlit, mesma categoria de
  código já sem cobertura unitária direta neste projeto).
- `AppTest` (`test_mapa_operacional_painel.py`, 6 casos): sem exceção -
  confirma que `calendar_input(...)` executa como Python real (AppTest
  roda o script inteiro linha a linha, não é só um smoke test de HTTP)
  sem lançar, inclusive no caminho onde nada foi clicado ainda
  (`None`, o caminho mais comum no primeiro carregamento da tela).
- Smoke test real (`streamlit run painel/app.py` em background, HTTP
  200 em `/_stcore/health` e na URL da página do mapa, sem traceback no
  log do servidor).
- Leitura direta do CSS/JS do pacote instalado (não documentação
  externa) para confirmar o comportamento real do componente (grid de
  mês sempre visível, não dropdown) antes de desenhar a integração -
  evitou construir a UI em cima de uma suposição errada.

## Validação NÃO realizada

- Renderização visual real num navegador (mesma limitação de sempre) -
  **mais importante aqui do que em qualquer outra mudança desta sessão**,
  já que é a primeira vez que este projeto depende de um componente de
  terceiro pequeno/pouco maduro. Se o calendário não renderizar
  corretamente ou o clique não funcionar como esperado no navegador
  real, o fallback (Jornada mostrando todas as jornadas do colaborador,
  sem depender do calendário) já garante que a tela continua utilizável
  enquanto se decide se vale a pena continuar com o pacote, trocar para
  `streamlit-calendar`, ou usar a alternativa sem dependência (contagem
  de pulsos no rótulo do selectbox).

## Arquivos afetados

- `requirements.txt` (`streamlit-calendar-input==0.0.3`, versão fixada).
- `painel/telas/mapa_operacional.py` (filtro Colaborador/Jornada
  separado, calendário de dias com jornada).
