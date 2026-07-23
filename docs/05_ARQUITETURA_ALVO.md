# Arquitetura alvo

## Aplicações
- PWA/captura: HTML, CSS e JavaScript instalável, com IndexedDB, Service Worker e API de geolocalização.
- Painel: Streamlit.
- API: FastAPI.
- Banco: PostgreSQL/Neon no MVP, preparado para ambiente corporativo.
- Storage: Supabase quando houver anexos.
- Dashboards: Apache ECharts via `streamlit-echarts`.
- Mapa: Folium/Leaflet inicialmente.

## Componentes
1. Autenticação e perfil.
2. Motor de jornada.
3. Máquina de estados do evento.
4. Catálogos.
5. Telemetria GPS.
6. Fila offline.
7. API idempotente de sincronização.
8. Consolidador de HH.
9. Falhas e RASF.
10. Analytics, mapa e exportações.

## Ambientes
- dev: desenvolvimento e dados de teste;
- homolog: validação com usuários reais;
- prod: somente após critérios de aceite.

## Princípio
O painel visual nunca é a fonte do tempo. A fonte é o log de eventos persistido.
