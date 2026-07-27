// Upload de foto do atendimento de falha para o backend (D3 do roteiro
// combinado apos o ADR-0021, que envia ao Supabase Storage).
//
// Best-effort, mesmo espirito de sincronizacao.js: uma falha de rede ou
// do backend nunca impede o preenchimento/encerramento do atendimento -
// foto e opcional (decisao do responsavel pelo produto). Nunca lanca para
// quem chama.

import { URL_BASE_API, TOKEN_SINCRONIZACAO, sincronizacaoConfigurada } from "./configSincronizacao.js";

// `opcoes` permite substituir fetch/URL/token/configurada em teste, mesmo
// padrao de sincronizacao.js::sincronizar.
export async function enviarFoto(arquivo, opcoes = {}) {
  const {
    fetchImpl = fetch,
    urlBase = URL_BASE_API,
    token = TOKEN_SINCRONIZACAO,
    configurada = sincronizacaoConfigurada(),
  } = opcoes;

  if (!configurada) {
    return {
      ok: false,
      mensagem: "Sincronização não configurada - não é possível enviar a foto agora.",
    };
  }

  const formData = new FormData();
  formData.append("arquivo", arquivo);

  let resposta;
  try {
    resposta = await fetchImpl(`${urlBase}/fotos`, {
      method: "POST",
      headers: { "X-Sync-Token": token },
      body: formData,
    });
  } catch (erro) {
    return { ok: false, mensagem: "Sem conexão com o backend agora." };
  }
  if (!resposta.ok) {
    return { ok: false, mensagem: `Backend recusou o envio da foto (HTTP ${resposta.status}).` };
  }
  const corpo = await resposta.json();
  return { ok: true, caminho: corpo.caminho, mensagem: "Foto enviada." };
}
