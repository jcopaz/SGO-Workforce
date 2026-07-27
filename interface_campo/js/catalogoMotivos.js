// Catalogo dinamico de motivos de pausa (docs/46_ADR_0019_CATALOGO_DINAMICO.md).
//
// Antes deste incremento, os motivos de pausa ficavam hardcoded em
// app.js. Agora o app busca o catalogo do backend (GET /catalogo,
// workforce_api) e guarda uma copia em cache local para continuar
// funcionando offline - mesmo principio de offline-first do resto do
// app (ADR-0004): uma falha de rede aqui nunca pode impedir o
// colaborador de registrar uma pausa.

import { URL_BASE_API, TOKEN_SINCRONIZACAO, sincronizacaoConfigurada } from "./configSincronizacao.js";

const CHAVE_CACHE = "sgo_workforce_catalogo_motivos_cache";

const memoriaFallback = new Map();

function armazenamentoDisponivel() {
  return typeof localStorage !== "undefined";
}

function lerCache() {
  const bruto = armazenamentoDisponivel()
    ? localStorage.getItem(CHAVE_CACHE)
    : memoriaFallback.get(CHAVE_CACHE) ?? null;
  if (!bruto) return null;
  try {
    return JSON.parse(bruto);
  } catch (erro) {
    return null;
  }
}

function gravarCache(lista) {
  const bruto = JSON.stringify(lista);
  if (armazenamentoDisponivel()) {
    localStorage.setItem(CHAVE_CACHE, bruto);
  } else {
    memoriaFallback.set(CHAVE_CACHE, bruto);
  }
}

// Ultimo recurso: so usado se o app nunca conseguiu buscar o catalogo do
// backend nem tem cache de uma consulta anterior (ex.: primeiro uso, ja
// offline). Espelha o seed real do backend (catalogo_relatorio_1_manutencao,
// ADR-0019) - garante que nenhum dos dois seletores (pausa, evento
// secundario) fica vazio mesmo no primeiro uso offline.
// Renumerado em 2026-07-27 (ADR-0023): antigo EE21 "SMS" -> EE20 "DDS / APR",
// antigo EE23 "Treinamento" -> EE22 (mesmo nome).
// tipo_evento_secundario adicionado no incremento de Evento Secundario na
// interface de campo (mapeamento do ADR-0014, EE01 classificado como APOIO
// por decisao do responsavel pelo produto em 2026-07-28).
const CATALOGO_MINIMO_OFFLINE = [
  { codigo: "EE01", descricao: "Preparação para jornada", tipo_registro: "evento_secundario", ativo: true, tipo_evento_secundario: "APOIO" },
  { codigo: "EE02", descricao: "Refeição 1 hora", tipo_registro: "pausa", ativo: true, tipo_evento_secundario: null },
  { codigo: "EE03", descricao: "Aguardando CCO", tipo_registro: "evento_secundario", ativo: true, tipo_evento_secundario: "ESPERA" },
  { codigo: "EE04", descricao: "Falta de ferramenta ou material", tipo_registro: "evento_secundario", ativo: true, tipo_evento_secundario: "ESPERA" },
  { codigo: "EE05", descricao: "Trem parado na frente de serviço", tipo_registro: "evento_secundario", ativo: true, tipo_evento_secundario: "ESPERA" },
  { codigo: "EE06", descricao: "Restrição de infraestrutura", tipo_registro: "evento_secundario", ativo: true, tipo_evento_secundario: "ESPERA" },
  { codigo: "EE07", descricao: "Reunião ou ADM", tipo_registro: "pausa", ativo: true, tipo_evento_secundario: null },
  { codigo: "EE08", descricao: "Serviço interno da coordenação", tipo_registro: "evento_secundario", ativo: true, tipo_evento_secundario: "APOIO" },
  { codigo: "EE09", descricao: "Trabalho não distribuído", tipo_registro: "evento_secundario", ativo: true, tipo_evento_secundario: "ESPERA" },
  { codigo: "EE10", descricao: "Aguardando sequência de serviço", tipo_registro: "evento_secundario", ativo: true, tipo_evento_secundario: "ESPERA" },
  { codigo: "EE11", descricao: "Consulta à documentação técnica", tipo_registro: "pausa", ativo: true, tipo_evento_secundario: null },
  { codigo: "EE12", descricao: "Deslocamento rodoviário", tipo_registro: "evento_secundario", ativo: true, tipo_evento_secundario: "DESLOCAMENTO" },
  { codigo: "EE13", descricao: "Deslocamento ferroviário", tipo_registro: "evento_secundario", ativo: true, tipo_evento_secundario: "DESLOCAMENTO" },
  { codigo: "EE14", descricao: "Deslocamento a pé", tipo_registro: "evento_secundario", ativo: true, tipo_evento_secundario: "DESLOCAMENTO" },
  { codigo: "EE15", descricao: "Preparar atividade", tipo_registro: "evento_secundario", ativo: true, tipo_evento_secundario: "APOIO" },
  { codigo: "EE16", descricao: "Desmontar atividade", tipo_registro: "evento_secundario", ativo: true, tipo_evento_secundario: "APOIO" },
  { codigo: "EE18", descricao: "Carregar veículo", tipo_registro: "evento_secundario", ativo: true, tipo_evento_secundario: "APOIO" },
  { codigo: "EE19", descricao: "Descarregar veículo", tipo_registro: "evento_secundario", ativo: true, tipo_evento_secundario: "APOIO" },
  { codigo: "EE20", descricao: "DDS / APR", tipo_registro: "pausa", ativo: true, tipo_evento_secundario: null },
  { codigo: "EE22", descricao: "Treinamento", tipo_registro: "pausa", ativo: true, tipo_evento_secundario: null },
];

function filtrarPorTipoRegistro(lista, tipoRegistro) {
  return lista.filter((motivo) => motivo.tipo_registro === tipoRegistro && motivo.ativo);
}

// Busca o catalogo completo do backend, com fallback em cascata:
// 1. GET /catalogo bem-sucedido -> grava cache, retorna a lista completa.
// 2. Falha de rede ou sincronizacao nao configurada -> usa o cache da
//    ultima consulta bem-sucedida, se existir.
// 3. Nunca teve cache (primeiro uso ja offline) -> lista minima embutida.
// `opcoes` permite substituir fetch/URL/token/configurada em teste, sem
// tocar nos valores reais de configSincronizacao.js - mesmo padrao de
// sincronizacao.js::sincronizar(). Por padrao usa exatamente o que o app
// real usa. Compartilhado por obterMotivosPausa/obterEventosSecundarios
// para nao buscar o catalogo duas vezes com filtros diferentes.
async function buscarCatalogoCompleto(opcoes) {
  const {
    fetchImpl = fetch,
    urlBase = URL_BASE_API,
    token = TOKEN_SINCRONIZACAO,
    configurada = sincronizacaoConfigurada(),
  } = opcoes;

  if (configurada) {
    try {
      const resposta = await fetchImpl(`${urlBase}/catalogo`, {
        headers: { "X-Sync-Token": token },
      });
      if (resposta.ok) {
        const lista = await resposta.json();
        gravarCache(lista);
        return lista;
      }
    } catch (erro) {
      // Sem conexao - cai no cache/fallback abaixo, nunca trava o app.
    }
  }
  const cache = lerCache();
  if (cache) {
    return cache;
  }
  return CATALOGO_MINIMO_OFFLINE;
}

export async function obterMotivosPausa(opcoes = {}) {
  const lista = await buscarCatalogoCompleto(opcoes);
  return filtrarPorTipoRegistro(lista, "pausa");
}

// Deslocamento, espera ou apoio (ADR-0005) - incremento de Evento
// Secundario na interface de campo. Cada entrada traz
// tipo_evento_secundario (DESLOCAMENTO/ESPERA/APOIO) para
// motor.iniciarEventoSecundario nao precisar de um segundo mapeamento
// manual na interface.
export async function obterEventosSecundarios(opcoes = {}) {
  const lista = await buscarCatalogoCompleto(opcoes);
  return filtrarPorTipoRegistro(lista, "evento_secundario");
}

// So para os testes isolarem o cache entre casos - o app real nunca
// chama isso (nao existe um botao "esquecer catalogo salvo" na interface).
export function _limparCacheParaTeste() {
  if (armazenamentoDisponivel()) {
    localStorage.removeItem(CHAVE_CACHE);
  }
  memoriaFallback.delete(CHAVE_CACHE);
}
