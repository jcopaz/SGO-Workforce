# Integração futura com o SGO

## Alvos
- autenticação/SSO;
- usuários, perfis e escopos;
- base de OS programadas;
- ativos, pátios e coordenadas;
- retorno de HH real por OS;
- falhas relacionadas a execução;
- dashboard unificado.

## Contratos sugeridos
- `GET /integracao/os` para snapshot autorizado;
- `GET /integracao/ativos`;
- `GET /integracao/usuarios`;
- `POST /integracao/hh-real`;
- eventos de atualização com versão e timestamp.

## Estratégia
Primeiro integração por leitura/snapshot. Depois escrita controlada. Não compartilhar diretamente tabelas internas entre aplicações sem contrato.

## Chaves
OS pode ser reaproveitada em ciclos SAP. Toda associação futura deve carregar ciclo/plano/data de importação, não apenas o número da OS.
