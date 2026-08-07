// Configuracao da integracao com o SGO (Gestao_OS) - ADR pendente de numero
// (integracao SGO Workforce <-> SGO, decidida em 2026-08-07).
//
// URL_API_SGO: base do api.py do SGO no Render (sem barra no final).
// URL_APP_SGO: URL publica do app.py (Streamlit Cloud) - para onde o EE17
// abre em nova aba com o token de sessao.
// CHAVE_API_SGO: mesmo valor configurado em WORKFORCE_API_KEY_SECRET no
// Render do SGO (api.py).
//
// AVISO DE SEGURANCA (mesmo aviso de configSincronizacao.js): este arquivo
// faz parte do site estatico publicado - qualquer pessoa pode ler a chave
// aqui inspecionando o codigo-fonte da pagina. Ela NAO e confidencial por
// si so - protege /auth/validar de uso acidental por quem nao conhece a
// URL, nao de um atacante determinado que leia o codigo do site. A
// seguranca real de /auth/validar e' o par usuario+senha de verdade
// (conferido no Postgres do SGO), que esta chave sozinha nao revela.
// Apontando para o ambiente DEV do SGO por enquanto (2026-08-07) - api.py
// ainda nao existe em nenhum ambiente de producao (so foi publicado no
// Render de dev, api-sgo-mrs-dev). Trocar para as URLs de producao
// quando o responsavel do produto validar o fluxo em dev e decidir
// promover - ver docs/90_ADR_0062_...md.
export const URL_API_SGO = "https://api-sgo-mrs.onrender.com";
export const URL_APP_SGO = "https://gestao-mrs-dev.streamlit.app";
export const CHAVE_API_SGO = "f3a9b7d2e8c14a6091f5b3d7c2e9a4f8b1d6e3c7a5f9b2d8e4c1a7f3b9d5e2c6";

// Mesmo padrao de sincronizacaoConfigurada() (configSincronizacao.js):
// enquanto os valores acima nao forem preenchidos de verdade, a integracao
// fica desligada (integracaoSgo.js nao tenta nenhuma chamada de rede) - o
// EE17 cai direto no formulario local de OS, sem tentar e falhar a toa.
export function integracaoSgoConfigurada() {
  return (
    Boolean(URL_API_SGO) &&
    Boolean(URL_APP_SGO) &&
    Boolean(CHAVE_API_SGO) &&
    CHAVE_API_SGO !== "SEU-WORKFORCE-API-KEY-AQUI"
  );
}
