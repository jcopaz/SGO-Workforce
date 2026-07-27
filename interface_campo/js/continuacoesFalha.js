// Transferencia de atendimento de falha entre colaboradores ("Falha nao
// Concluida", D4 do roteiro combinado apos o ADR-0021).
//
// Best-effort, mesmo espirito de sincronizacao.js: sem conexao,
// simplesmente nao ha transferencia (o colaborador de origem ainda
// encerra a atividade localmente via MotorJornada.transferirAtendimentoFalha
// - so o aviso ao proximo colaborador depende do backend). Nunca lanca.
//
// So os campos obrigatorios do D1 (nota/ativo/sintoma/objeto/observacao)
// viajam entre colaboradores - GPS e foto sao especificos de quem
// capturou (dispositivo/localizacao), nao fazem sentido pre-preenchidos
// para outra pessoa.

import { URL_BASE_API, TOKEN_SINCRONIZACAO, sincronizacaoConfigurada } from "./configSincronizacao.js";

function dadosFalhaParaPayload(dados) {
  return {
    nota: dados.nota,
    ativo: dados.ativo,
    sintoma: dados.sintoma,
    objeto: dados.objeto,
    observacao: dados.observacao,
  };
}

export async function criarContinuacao(dadosFalha, matriculaDestino, opcoes = {}) {
  const {
    fetchImpl = fetch,
    urlBase = URL_BASE_API,
    token = TOKEN_SINCRONIZACAO,
    configurada = sincronizacaoConfigurada(),
  } = opcoes;

  if (!configurada) {
    return {
      ok: false,
      mensagem: "Sincronização não configurada - o próximo colaborador não será avisado automaticamente.",
    };
  }

  try {
    const resposta = await fetchImpl(`${urlBase}/continuacoes-falha`, {
      method: "POST",
      headers: { "Content-Type": "application/json", "X-Sync-Token": token },
      body: JSON.stringify({
        matricula_destino: matriculaDestino,
        dados: dadosFalhaParaPayload(dadosFalha),
      }),
    });
    if (!resposta.ok) {
      return { ok: false, mensagem: `Backend recusou a transferência (HTTP ${resposta.status}).` };
    }
    return { ok: true, mensagem: "Transferência registrada no backend." };
  } catch (erro) {
    return { ok: false, mensagem: "Sem conexão com o backend agora." };
  }
}

// Devolve a continuacao pendente mais antiga para a matricula, ou null
// (sem conexao, sem configuracao, matricula vazia ou nenhuma pendencia).
export async function buscarPendente(matricula, opcoes = {}) {
  const {
    fetchImpl = fetch,
    urlBase = URL_BASE_API,
    token = TOKEN_SINCRONIZACAO,
    configurada = sincronizacaoConfigurada(),
  } = opcoes;

  if (!configurada || !matricula) return null;

  try {
    const resposta = await fetchImpl(
      `${urlBase}/continuacoes-falha?matricula=${encodeURIComponent(matricula)}`,
      { headers: { "X-Sync-Token": token } }
    );
    if (!resposta.ok) return null;
    const lista = await resposta.json();
    return lista.length > 0 ? lista[0] : null;
  } catch (erro) {
    return null;
  }
}

export async function marcarConsumida(id, opcoes = {}) {
  const {
    fetchImpl = fetch,
    urlBase = URL_BASE_API,
    token = TOKEN_SINCRONIZACAO,
    configurada = sincronizacaoConfigurada(),
  } = opcoes;

  if (!configurada) return { ok: false };

  try {
    const resposta = await fetchImpl(`${urlBase}/continuacoes-falha/${id}/consumir`, {
      method: "POST",
      headers: { "X-Sync-Token": token },
    });
    return { ok: resposta.ok };
  } catch (erro) {
    return { ok: false };
  }
}
