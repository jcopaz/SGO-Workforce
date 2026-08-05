# ADR-0054 | Qualidade de GPS wireada, foto de falha exibida no painel, expurgo de pulsos antigos e correção do CLAUDE.md

## Contexto

Depois de fechar o lote de decisões do ADR-0053, o responsável pelo
produto pediu para avançar em todas as melhorias técnicas pendentes que
não dependem de decisão de negócio nova. Um levantamento no código real
(não só nos docs, que estavam desatualizados em vários pontos) encontrou
quatro lacunas concretas, detalhadas abaixo. Uma delas (limiares de
qualidade de GPS) tinha uma decisão de negócio genuína em aberto -
perguntada e aprovada antes de codificar (ver decisão 1).

## Decisões

### 1. Limiares de qualidade de GPS aprovados e wireados

`workforce_core/qualidade_gps.py::avaliar_pulso` existia desde o
Incremento 7, testado, mas nunca era chamado em produção - nenhum lugar
do pipeline (captura, sincronização, backend, painel) definia os dois
limiares que a função exige como parâmetro obrigatório
(`precisao_maxima_aceitavel_metros`, `velocidade_maxima_plausivel_metros_segundo`).
Isso está diretamente relacionado a um bug relatado em produção: o pulso
final de uma jornada real (matrícula 30028203, encerrada 17:20:55 em
2026-08-05) apareceu no mapa longe da posição real, sem nenhum filtro
capaz de sinalizar isso.

Perguntado ao responsável pelo produto (`AskUserQuestion`, "engenharia
propõe, produto aprova" conforme já registrado no ADR-0043): aprovados os
valores recomendados -

- **Precisão máxima aceitável: 100 metros** (acima disso, `PRECISAO_RUIM`).
- **Velocidade máxima plausível: 50 m/s (~180 km/h)** (acima disso entre
  dois pulsos consecutivos, `SALTO_IMPOSSIVEL`) - folga generosa para
  caminhão em rodovia, sem deixar passar um salto de GPS impossível.

Implementação (`painel/dados.py`):
- Constantes `PRECISAO_MAXIMA_ACEITAVEL_METROS`/`VELOCIDADE_MAXIMA_PLAUSIVEL_METROS_SEGUNDO`
  na fronteira de apresentação (não dentro de `qualidade_gps.py` - mesmo
  princípio de `fuso_horario`, o domínio nunca embute constante de
  negócio).
- `reclassificar_qualidade_pulsos(pulsos)`: ordena por
  `timestamp_dispositivo`, chama `avaliar_pulso` em sequência (o pulso
  anterior cronológico, não o anterior na lista recebida), devolve uma
  lista nova via `dataclasses.replace` - nunca sobrescreve o pulso
  original recebido do backend. Recalcula a cada carregamento (não existe
  migração/backfill no Postgres) - por isso reclassifica retroativamente
  inclusive pulsos antigos já gravados, sem precisar de nenhuma migração.
  Chamada dentro do `@st.cache_data` de `_carregar_pulsos_cache`
  (`painel/telas/mapa_operacional.py`) sobre a jornada inteira, **antes**
  de qualquer filtro de período recortar pontos e quebrar a noção de
  "pulso anterior".

No mapa (`painel/mapa.py`):
- Pulso suspeito (`qualidade` diferente de `OK`/`NAO_AVALIADO`) ganha
  marcador visualmente distinto (borda vermelha grossa tracejada,
  `_COR_QUALIDADE_SUSPEITA`) - continua desenhado (docs/08: "marcados,
  nao apagados", regra de ouro 8 do CLAUDE.md), só fica identificável.
- Trajetória (`simplificar_trajetoria`) e clusters de permanência
  (`agrupar_permanencia`) - camadas de **inferência**, diferente do pulso
  bruto - passam a receber só `pulsos_confiaveis` (OK ou NAO_AVALIADO),
  nunca um pulso suspeito. É exatamente o caso do bug relatado: o pulso
  final errado deixa de puxar a linha de trajetória até ele.

### 2. Foto de atendimento de falha exibida no painel

Upload existia desde o ADR-0022 (Supabase Storage, `POST /fotos`), e já
havia até um endpoint pronto para gerar URL assinada (`GET /fotos/url`,
service_role key nunca sai do backend) - mas nada no painel usava
qualquer um dos dois. `LinhaAtendimentoFalha` (`workforce_core/consolidacao.py`)
ganhou o campo `foto_caminho` (default `None`, para não quebrar as ~20
construções diretas já existentes em teste). Aba Falhas
(`painel/telas/falhas.py`): coluna "Foto" (📷/--) na tabela "Todos os
atendimentos", e um `st.expander` "Fotos de atendimentos" (só aparece se
houver pelo menos um atendimento com foto) com seletor + botão "Carregar
foto" - busca sob demanda (nunca automático a cada rerun, já que a URL
assinada expira em 1h) via nova `dados.obter_url_foto_falha`.

### 3. Expurgo de pulsos GPS com mais de 90 dias

ADR-0043 decidiu 90 dias de retenção, nunca implementado. Novo endpoint
`POST /pulsos/expurgar?dias=90` (`src/workforce_api/app.py`, mesmo token
fixo dos demais, `dias < 1` recusado com 400 para não apagar tudo por um
erro de digitação). `RepositorioPulsosGpsPostgres.apagar_pulsos_anteriores_a`
usa a coluna `criado_em` (momento em que o **servidor** recebeu o pulso,
`DEFAULT now()` desde sempre, sem backfill necessário) - relógio de
servidor é confiável por construção, relógio de celular não (mesmo
espírito da regra de ouro 3 do CLAUDE.md, aplicada aqui a retenção em vez
de cálculo de HH). `RepositorioPulsosGpsArquivo` ganhou o mesmo método
(aproximado por `timestamp_dispositivo`, já que o armazenamento local não
tem um metadado de recebimento por linha) - só para os testes/uso local
funcionarem igual, nunca é a fonte de verdade de produção.

Ação manual, não agendada: `painel/telas/configuracoes_catalogo.py`
ganhou uma seção "Manutenção de dados" com o número de dias, uma
confirmação explícita obrigatória (checkbox) antes do botão "Expurgar
pulsos antigos" habilitar - ação permanente e irreversível, sem
agendamento automático porque não há infraestrutura de cron neste piloto.

### 4. CLAUDE.md desatualizado em relação ao ADR-0021

A regra de ouro 6 e a premissa consolidada sobre atendimento de falha
ainda diziam "nota, ativo, sintoma, causa, ação" - o ADR-0021
(2026-07-27) já tinha simplificado isso para "nota, ativo, sintoma,
objeto, observação" (causa/ação viraram um único campo livre de
observação), e o guia mestre do projeto nunca foi atualizado para
refletir a própria decisão já tomada. Corrigido nas duas linhas, com
referência explícita ao ADR-0021. Não é decisão de negócio nova - é
sincronizar a documentação com uma decisão que já existia no código.

## Validação de qualidade realizada

- `python -m py_compile` em todos os módulos tocados.
- `pytest` completo: 391 passed (13 testes novos: 5 em `test_mapa.py`
  para qualidade de GPS, 2 em `test_falhas_painel.py` para a foto, 4 em
  `test_gps.py` + 5 em `test_workforce_api.py` para o expurgo, 4 em
  `test_configuracoes_catalogo_painel.py`, novo).
- `AppTest` cobrindo os três fluxos de UI novos (foto de falha,
  expurgo com botão desabilitado/habilitado, erro de rede tratado sem
  quebrar a tela).

## Validação NÃO realizada

- Teste manual em navegador/celular real de qualquer uma das três telas
  tocadas (mesma limitação de sempre).
- O bug original (pulso final em local errado) não foi confirmado
  resolvido pelo usuário - a reclassificação retroativa deveria marcar
  esse pulso especificamente na próxima vez que a jornada for aberta no
  mapa, mas isso depende do valor real de precisão/velocidade daquele
  pulso, nunca confirmado.
- Expurgo de pulsos nunca foi exercitado contra o Postgres real (só o
  repositório de arquivo, usado nos testes).

## Arquivos afetados

- `painel/dados.py` (`reclassificar_qualidade_pulsos`, `obter_url_foto_falha`).
- `painel/mapa.py` (marcador suspeito, filtro de trajetória/cluster).
- `painel/telas/mapa_operacional.py` (reclassificação no cache de pulsos).
- `painel/telas/falhas.py` (coluna Foto, seção de fotos).
- `painel/telas/configuracoes_catalogo.py` (seção de expurgo).
- `src/workforce_core/consolidacao.py` (`LinhaAtendimentoFalha.foto_caminho`).
- `src/workforce_api/app.py` (`POST /pulsos/expurgar`).
- `src/workforce_api/repositorio_pulsos_postgres.py`,
  `src/workforce_storage/repositorio_pulsos_gps.py` (`apagar_pulsos_anteriores_a`).
- `CLAUDE.md` (regra de ouro 6, premissa de atendimento de falha).
- `tests/test_mapa.py`, `tests/test_falhas_painel.py`, `tests/test_gps.py`,
  `tests/test_workforce_api.py`, `tests/test_configuracoes_catalogo_painel.py` (novo).

## Data e responsáveis

- Data de registro: 2026-08-05.
- Registrado por: Claude Code, a pedido do responsável pelo produto
  (j.copaz@hotmail.com). Limiares de qualidade de GPS aprovados
  explicitamente antes da implementação; as outras três frentes são
  lacunas técnicas puras, sem decisão de negócio nova envolvida.
