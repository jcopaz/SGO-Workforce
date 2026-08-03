# ADR-0042 | Levantamento: o que falta para captação real de pulso GPS/geolocalização

## Contexto

Referenciado (mas não escrito) no ADR-0041, seção 1: ao remover o
seletor de fonte de dados de `dashboard.py`/`falhas.py`, ficou
registrado que `mapa_operacional.py`, `capacidade_pcm.py` e
`dados_exportacoes.py` continuam só em arquivo local, "uma lacuna de
arquitetura, não um ajuste de UI". O responsável do produto pediu
explicitamente, na mesma sessão, um levantamento de "o que falta para
avançarmos para a captação do pulso, ou seja, a geolocalização" antes
de decidir os próximos passos do projeto.

Este documento **não é uma decisão de arquitetura** - é um
levantamento de estado real (não do que a documentação promete, mas do
que o código de fato faz), feito para embasar a próxima decisão do
responsável do produto. Nenhum código foi alterado para produzir este
levantamento.

## Resumo executivo

Existe um **motor de domínio completo e testado** para pulsos GPS
periódicos (`PulsoGps`, avaliação de qualidade, repositório
append-only, sincronizador em lote por cursor) - mas ele **nunca é
alimentado por dado real**. A interface de campo não captura pulsos
periódicos em lugar nenhum do código - a única captura real de GPS é
pontual, sob toque do colaborador, no atendimento de falha. O backend
hospedado (FastAPI + Postgres, real) não tem nenhum endpoint de
pulsos. O mapa operacional (Folium, real) só lê de arquivo local, e a
única forma de ele mostrar algo hoje é um botão que fabrica dados
aleatórios. Tudo isso já era **documentado explicitamente** desde o
ADR-0007 como "deliberadamente fora de escopo", com lista nomeada do
que falta.

## O que já existe e funciona de verdade

- **`PulsoGps`** (`src/workforce_core/entities.py:149-173`): latitude,
  longitude, precisão, timestamp do dispositivo, velocidade/direção
  opcionais, `QualidadePulso` (NAO_AVALIADO/OK/PRECISAO_RUIM/
  SALTO_IMPOSSIVEL/VELOCIDADE_INCOMPATIVEL).
- **`src/workforce_core/qualidade_gps.py`**: avalia precisão ruim,
  salto impossível (velocidade implícita entre pulsos consecutivos) e
  velocidade incompatível reportada pelo dispositivo. Nunca sobrescreve
  a precisão original. Limiares numéricos (precisão máxima aceitável,
  velocidade máxima plausível) são sempre parâmetro obrigatório de
  quem chama - nunca têm valor padrão embutido no código (decisão de
  negócio deliberadamente não tomada ainda).
- **`src/workforce_core/geo.py`**: `simplificar_trajetoria` e
  `agrupar_permanencia` (clusters de permanência) - usados pelo mapa.
- **`RepositorioPulsosGpsArquivo`**
  (`src/workforce_storage/repositorio_pulsos_gps.py`): `.jsonl`
  append-only por jornada, linha corrompida não apaga as demais. Só
  arquivo local - sem versão que persista em banco/backend real.
- **`SincronizadorPulsos`/`CursorSincronizacaoPulsos`**
  (`src/workforce_sync/`): implementa a regra de ouro 7 (enfileira e
  sincroniza em lote, só avança o cursor se o lote inteiro for aceito,
  reenvio após ack perdido não duplica). Algoritmo testado e correto -
  mas o transporte usado é `ClienteSincronizacaoEmMemoria`, um fake
  documentado no próprio arquivo como substituto de uma API real que
  "não existe ainda... para pulsos".
- **Mapa operacional** (`painel/mapa.py` + `painel/telas/
  mapa_operacional.py`): Folium real, 3 camadas (pulsos coloridos por
  qualidade, trajetória simplificada, clusters de permanência com
  popup avisando "inferência, não prova de presença"), popups escapam
  HTML. Testado (`tests/test_geo.py`, `tests/test_mapa.py`). Mas **lê
  só de diretório local**, nunca de API.
- **Captura pontual de GPS no atendimento de falha**
  (`interface_campo/js/geolocalizacao.js`): `navigator.geolocation.
  getCurrentPosition` real, sob toque do colaborador, best-effort
  (nunca bloqueia o fluxo se falhar/for negado). Não é um "pulso" -
  os campos ficam dentro de `DadosFalha`, não de `PulsoGps`, e viajam
  pela sincronização normal de jornada. Testado
  (`tests/js/geolocalizacao.test.mjs`).
- **Backend hospedado real** (`src/workforce_api/app.py`, FastAPI +
  Postgres no Render, autenticação por `X-Sync-Token` fail-closed):
  endpoints reais de jornadas, catálogo, fotos (Supabase Storage) e
  continuações de falha. **Nenhum endpoint de pulsos GPS.**

## O que existe só como simulação/fixture de teste

- **`gerar_pulsos_exemplo`** (`painel/dados.py`): pulsos fabricados
  (seed determinística por jornada) a partir de um "ponto de
  referência arbitrário" (Praça da Sé, SP) - a própria docstring
  explica que é "para demonstrar o mapa operacional sem depender de
  captura real de GPS (que não existe em `interface_campo/js/`)".
  Acionado por um botão em `mapa_operacional.py`.
- **`ClienteSincronizacaoEmMemoria`** (`src/workforce_sync/
  cliente.py`): simula um servidor idempotente em memória - não há
  implementação HTTP real deste transporte para pulsos.
- **`carregar_pulsos_via_api` não existe** - só `carregar_pulsos`
  (arquivo local). Confirma o que os nomes já sugeriam.

## O que está documentado como decisão pendente

- **`docs/34_ADR_0007_PULSOS_GPS_QUALIDADE_E_SINCRONIZACAO_LOTE.md`**:
  lista nomeada - captura real no navegador (exige teste em
  dispositivo real), limiares numéricos de qualidade, obrigatoriedade
  de GPS, política de contingência para GPS indisponível, retenção,
  perfis autorizados a ver trajetória, avaliação LGPD/segurança da
  informação - "nada disso foi endereçado, este incremento é
  infraestrutura técnica, não aprovação de uso em produção".
- **`docs/08_GPS_PULSOS_E_PRIVACIDADE.md`**: seção "Privacidade" ainda
  aberta - sinal visível de captura ativa, retenção, acesso por
  perfil, avaliação prévia de LGPD/norma corporativa antes da
  produção.
- **`docs/23_DECISOES_PENDENTES.md`**: item 1 (intervalo padrão dos
  pulsos e impacto em bateria) ainda aberto; item 2 (política legal
  geral de rastreamento) resolvido por analogia em 2026-07-27, mas
  isso **não é** a avaliação LGPD específica de pulsos periódicos que
  o ADR-0007 continua pedindo; item 7 (obrigatoriedade de GPS) só
  resolvido para o atendimento de falha, não para pulsos periódicos;
  item 9 (nível de detalhe do mapa por perfil) ainda aberto.
- **`docs/27_ALINHAMENTO_OFICIAL_SGO_WORKFORCE_v1_2.md`**, seção
  15.3: lista consolidada das mesmas pendências (intervalo, política
  adaptativa por bateria/movimento, obrigatoriedade, contingência,
  precisão mínima, retenção, perfis, LGPD).
- **`docs/37_ADR_0010_MAPA_OPERACIONAL_FOLIUM.md`**: sem autenticação/
  perfis no sistema ainda, "qualquer pessoa com acesso ao painel vê
  todos os pulsos"; renderização Folium nunca validada em navegador
  real (mesma limitação de ambiente de sempre).

## O que não existe em lugar nenhum

- Captura periódica de GPS (`watchPosition`) em `interface_campo/js/` -
  zero ocorrências; a própria tela (`index.html`) avisa isso ao
  colaborador.
- Fila/store de IndexedDB dedicado a pulsos no navegador
  (`armazenamento.js` só tem store de jornadas) - mesmo que a captura
  existisse, não há hoje estrutura de fila offline específica pra
  pulso no lado do cliente.
- Endpoint de pulsos na API real, tabela Postgres de pulsos, cliente
  HTTP real de sincronização de pulsos.
- Qualquer limiar numérico de precisão/velocidade codificado (é
  parâmetro obrigatório sempre, deliberado).
- Teste de "pulso repetido" (duplicata por reenvio) e teste de
  "relógio divergente" (skew entre timestamp do dispositivo e do
  servidor) - nenhum dos dois existe, embora ambos estejam nas
  "Validações mínimas" do `CLAUDE.md`.
- Retenção/expurgo de dado de localização, controle de acesso por
  perfil para pulsos/trajetórias (não há autenticação de usuário no
  sistema ainda), sinal visível de captura ativa para o colaborador,
  avaliação LGPD formal específica de pulso periódico contínuo.

## Não decidido aqui

Este documento não decide ordem de prioridade nem timeline - isso é
decisão do responsável do produto, feita em conversa separada depois
deste levantamento. Também não decide nenhum dos parâmetros de negócio
pendentes (intervalo de pulso, limiares de qualidade, obrigatoriedade,
retenção) - todos continuam explicitamente em aberto.

## Arquivos afetados

Nenhum - documento de levantamento, sem mudança de código.
