// Configuracao da sincronizacao real com o backend hospedado
// (docs/44_ADR_0017_SINCRONIZACAO_REAL_BACKEND_HOSPEDADO.md).
//
// Preencha URL_BASE_API com a URL publica do backend no Render (sem barra
// no final, ex.: "https://sgo-workforce-api.onrender.com") e
// TOKEN_SINCRONIZACAO com o mesmo valor configurado na variavel de
// ambiente SYNC_TOKEN do backend.
//
// AVISO DE SEGURANCA: este arquivo faz parte do site estatico publicado no
// Netlify - qualquer pessoa pode ler o token aqui inspecionando o
// codigo-fonte da pagina. Ele NAO e confidencial. Serve apenas para
// impedir que alguem que descubra a URL do backend por acaso escreva
// dados aleatorios nela - nao protege contra quem leia o codigo do site.

export const URL_BASE_API = "https://sgo-workforce.onrender.com";
export const TOKEN_SINCRONIZACAO = "jPQssLcPij6vQBBcedgEQenft9I3jTZ6tln3COSK1vU";

// Enquanto os valores acima nao forem preenchidos de verdade, a
// sincronizacao fica desligada (sincronizacao.js nao tenta nenhuma
// chamada de rede) - evita gastar tempo/bateria tentando falar com um
// endereco que nao existe.
export function sincronizacaoConfigurada() {
  return (
    Boolean(URL_BASE_API) &&
    !URL_BASE_API.includes("SEU-BACKEND") &&
    Boolean(TOKEN_SINCRONIZACAO) &&
    TOKEN_SINCRONIZACAO !== "SEU-TOKEN-AQUI"
  );
}
