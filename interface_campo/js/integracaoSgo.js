// Integracao com o SGO (Gestao_OS): valida login real do colaborador contra
// a base de usuarios do SGO (POST /auth/validar em api.py) e monta o link
// de SSO usado pelo EE17 para abrir a tela de apontamento de OS do SGO ja
// autenticada (ver docs do ADR pendente de numero, 2026-08-07).
//
// Best-effort, igual a sincronizacao.js: nunca lanca excecao para quem
// chama, e uma falha de rede (SEM CONEXAO) e' um resultado normal, nao um
// erro - o app continua funcionando offline, so sem a integracao com o SGO
// (EE17 cai no formulario local de numero de OS, ja existente).

import { URL_API_SGO, URL_APP_SGO, CHAVE_API_SGO, integracaoSgoConfigurada } from "./configSgo.js";

// `opcoes.fetchImpl` permite substituir fetch em teste, mesmo padrao de
// sincronizacao.js.
export async function validarLoginSgo(matricula, senha, opcoes = {}) {
  const { fetchImpl = fetch, configurada = integracaoSgoConfigurada() } = opcoes;

  if (!configurada) {
    return { ok: false, mensagem: "Integracao com o SGO nao configurada." };
  }

  const corpo = new URLSearchParams();
  corpo.set("username", matricula);
  corpo.set("senha", senha);

  let resposta;
  try {
    resposta = await fetchImpl(`${URL_API_SGO}/auth/validar`, {
      method: "POST",
      headers: {
        "x-api-key": CHAVE_API_SGO,
        "Content-Type": "application/x-www-form-urlencoded",
      },
      body: corpo,
    });
  } catch (erro) {
    return { ok: false, mensagem: "Sem conexao com o SGO (app continua funcionando offline)." };
  }

  if (resposta.status === 401) {
    return { ok: false, mensagem: "Matricula ou senha do SGO incorretas." };
  }
  if (resposta.status === 403) {
    // Cobre tanto "chave de integracao invalida/nao configurada no lado do
    // SGO" quanto "senha pendente de troca" (ver api.py) - a mensagem do
    // proprio backend ja distingue os dois casos.
    let detalhe = "Acesso ao SGO negado.";
    try {
      const corpoErro = await resposta.json();
      if (corpoErro && corpoErro.detail) detalhe = corpoErro.detail;
    } catch (erro) {
      // resposta sem corpo JSON - mantem a mensagem generica acima.
    }
    return { ok: false, mensagem: detalhe };
  }
  if (!resposta.ok) {
    return { ok: false, mensagem: `SGO recusou a validacao (HTTP ${resposta.status}).` };
  }

  const dados = await resposta.json();
  return {
    ok: true,
    username: dados.username,
    nome: dados.nome,
    perfil: dados.perfil,
    escopo: dados.escopo,
    governanca: dados.governanca,
    sid: dados.sid ?? null,
    obtidoEm: new Date(),
  };
}

// URL para abrir o SGO ja autenticado (nova aba - nunca substitui a aba do
// Workforce, que continua com a Atividade em andamento; "voltar" e' so
// trocar de aba). `sessao` e' o retorno de validarLoginSgo com ok:true.
// null quando nao ha sid (integracao nao configurada no lado do SGO ainda,
// ou login nao validado) - quem chama decide o fallback (formulario local
// de OS, ja existente).
export function linkApontamentoSgo(sessao) {
  if (!sessao || !sessao.sid) return null;
  return `${URL_APP_SGO}/?sid=${encodeURIComponent(sessao.sid)}`;
}
