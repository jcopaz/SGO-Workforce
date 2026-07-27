// Sincronizacao best-effort com o backend real (workforce_api), para que
// as jornadas registradas na interface de campo apareçam no painel
// gerencial (docs/44_ADR_0017_SINCRONIZACAO_REAL_BACKEND_HOSPEDADO.md).
//
// Nunca lanca excecao para quem chama: sincronizar e uma operacao
// auxiliar, e uma falha de rede/servidor nunca pode impedir o registro
// local do evento (mesmo principio de offline-first ja usado no resto do
// app - ver ADR-0004). Quem chama decide o que fazer com o resultado
// { ok, mensagem } (ex.: mostrar "nao sincronizado" na tela).

import { URL_BASE_API, TOKEN_SINCRONIZACAO, sincronizacaoConfigurada } from "./configSincronizacao.js";

function pausaParaPayload(pausa) {
  return {
    id: pausa.id,
    atividade_id: pausa.atividadeId,
    motivo: pausa.motivo,
    inicio: pausa.inicio ? pausa.inicio.toISOString() : null,
    fim: pausa.fim ? pausa.fim.toISOString() : null,
    estado: pausa.estado,
  };
}

// Mesmo contrato de workforce_storage.serializacao.dados_falha_para_dict -
// campos ausentes aqui (causa/acao/os_referencia) nao existem no
// formulario da interface de campo (ADR-0021) e ficam None do lado Python
// via dados_falha_de_dict (usa .get()).
function dadosFalhaParaPayload(dados) {
  if (!dados) return null;
  return {
    nota: dados.nota,
    ativo: dados.ativo,
    sintoma: dados.sintoma,
    objeto: dados.objeto,
    observacao: dados.observacao,
    gps_latitude: dados.gpsLatitude,
    gps_longitude: dados.gpsLongitude,
    gps_precisao_metros: dados.gpsPrecisaoMetros,
    gps_capturado_em: dados.gpsCapturadoEm ? dados.gpsCapturadoEm.toISOString() : null,
    foto_caminho: dados.fotoCaminho,
  };
}

// Mesmo contrato de workforce_storage.serializacao.ordem_servico_para_dict.
function ordemServicoParaPayload(ordem) {
  return {
    id: ordem.id,
    numero: ordem.numero,
    criada_em: ordem.criadaEm ? ordem.criadaEm.toISOString() : null,
    excluida: ordem.excluida,
  };
}

function atividadeParaPayload(atividade) {
  return {
    id: atividade.id,
    inicio: atividade.inicio ? atividade.inicio.toISOString() : null,
    fim: atividade.fim ? atividade.fim.toISOString() : null,
    estado: atividade.estado,
    pausas: atividade.pausas.map(pausaParaPayload),
    dados_falha: dadosFalhaParaPayload(atividade.dadosFalha),
    ordens_servico: atividade.ordensServico.map(ordemServicoParaPayload),
    resultado: atividade.resultado,
  };
}

// Mesmo contrato de workforce_storage.serializacao.evento_secundario_para_dict.
function eventoSecundarioParaPayload(evento) {
  return {
    id: evento.id,
    tipo: evento.tipo,
    motivo: evento.motivo,
    inicio: evento.inicio ? evento.inicio.toISOString() : null,
    fim: evento.fim ? evento.fim.toISOString() : null,
    estado: evento.estado,
  };
}

// Converte a jornada do formato do motor JS (camelCase) para o mesmo
// contrato que workforce_storage.serializacao.jornada_para_dict produz no
// lado Python - e o formato que workforce_api (POST /jornadas) espera
// receber.
export function paraPayloadSincronizacao(jornada) {
  return {
    formato_versao: 4,
    id: jornada.id,
    colaborador_matricula: jornada.colaboradorMatricula,
    inicio: jornada.inicio ? jornada.inicio.toISOString() : null,
    fim: jornada.fim ? jornada.fim.toISOString() : null,
    estado: jornada.estado,
    atividades: jornada.atividades.map(atividadeParaPayload),
    eventos_secundarios: jornada.eventosSecundarios.map(eventoSecundarioParaPayload),
  };
}

// `opcoes` permite substituir fetch/URL/token/configurada em teste, sem
// tocar nos valores reais de configSincronizacao.js - por padrao usa
// exatamente o que o app real usa.
export async function sincronizar(jornada, opcoes = {}) {
  const {
    fetchImpl = fetch,
    urlBase = URL_BASE_API,
    token = TOKEN_SINCRONIZACAO,
    configurada = sincronizacaoConfigurada(),
  } = opcoes;

  if (!configurada) {
    return { ok: false, mensagem: "Sincronizacao nao configurada." };
  }

  let resposta;
  try {
    resposta = await fetchImpl(`${urlBase}/jornadas`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-Sync-Token": token,
      },
      body: JSON.stringify(paraPayloadSincronizacao(jornada)),
    });
  } catch (erro) {
    return { ok: false, mensagem: "Sem conexao com o backend (app continua funcionando offline)." };
  }
  if (!resposta.ok) {
    return { ok: false, mensagem: `Backend recusou a sincronizacao (HTTP ${resposta.status}).` };
  }
  return { ok: true, mensagem: "Sincronizado com o backend." };
}
