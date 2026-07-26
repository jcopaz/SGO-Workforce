// Relogio simulado - ferramenta de TESTE (nao usar em operacao real).
//
// Motivacao: o motor de dominio (MotorJornada) ja recebe o timestamp
// `quando` explicitamente em toda transicao - ele nunca le o relogio
// sozinho (docs/07_MOTOR_EVENTOS_E_HH.md). O gargalo para testar o piloto
// era interface_campo/js/app.js chamar `new Date()` direto em cada botao,
// travando o teste manual no relogio real do aparelho. Este modulo
// substitui esse `new Date()` por um relogio que pode ser adiantado, para
// testar jornadas de varios dias sem esperar o tempo real passar
// (docs/43_ADR_0016_SIMULADOR_DE_TEMPO_PARA_TESTES.md).
//
// Estrategia: agora() = tempo real + deslocamento acumulado. O tempo
// simulado continua fluindo normalmente (nao fica congelado), so com um
// adiantamento - isso evita timestamps identicos em cliques sequenciais
// rapidos e torna "definir data exata" e "voltar ao tempo real" apenas um
// recalculo do deslocamento.
//
// O deslocamento fica em localStorage para sobreviver a recarregamentos da
// pagina (mesma necessidade de persistencia que motiva o IndexedDB em
// armazenamento.js). Quando localStorage nao existe (ambiente de teste em
// Node), cai para um Map em memoria - o modulo continua funcionando e
// testavel sem depender de API de navegador.

const CHAVE_DESLOCAMENTO = "sgo_workforce_relogio_simulado_deslocamento_ms";

const memoriaFallback = new Map();

function armazenamentoDisponivel() {
  return typeof localStorage !== "undefined";
}

function lerBruto() {
  if (armazenamentoDisponivel()) {
    return localStorage.getItem(CHAVE_DESLOCAMENTO);
  }
  return memoriaFallback.has(CHAVE_DESLOCAMENTO) ? memoriaFallback.get(CHAVE_DESLOCAMENTO) : null;
}

function gravarBruto(valor) {
  if (armazenamentoDisponivel()) {
    localStorage.setItem(CHAVE_DESLOCAMENTO, valor);
    return;
  }
  memoriaFallback.set(CHAVE_DESLOCAMENTO, valor);
}

function lerDeslocamentoMs() {
  const bruto = lerBruto();
  const numero = bruto === null ? 0 : Number(bruto);
  return Number.isFinite(numero) ? numero : 0;
}

function gravarDeslocamentoMs(deslocamentoMs) {
  gravarBruto(String(Math.trunc(deslocamentoMs)));
}

export const UM_MINUTO_MS = 60 * 1000;
export const UMA_HORA_MS = 60 * UM_MINUTO_MS;
export const UM_DIA_MS = 24 * UMA_HORA_MS;

// Instante efetivo que a interface de campo deve usar como "agora" em toda
// transicao do motor de dominio - substitui todo `new Date()` direto.
export function agora() {
  return new Date(Date.now() + lerDeslocamentoMs());
}

export function estaSimulando() {
  return lerDeslocamentoMs() !== 0;
}

export function avancar(deslocamentoAdicionalMs) {
  gravarDeslocamentoMs(lerDeslocamentoMs() + deslocamentoAdicionalMs);
}

// Recalcula o deslocamento para que agora() passe a coincidir com
// dataAlvo. Nao move nada retroativamente ja persistido - so muda o que
// as proximas transicoes vao gravar como timestamp.
export function definir(dataAlvo) {
  gravarDeslocamentoMs(dataAlvo.getTime() - Date.now());
}

export function voltarParaTempoReal() {
  gravarDeslocamentoMs(0);
}

// Texto curto para exibicao (ex.: "+1d 3h", "+45min", "-2h"). Nunca usado
// como fonte de calculo, so apresentacao do deslocamento ja acumulado.
export function descreverDeslocamento() {
  const deslocamentoMs = lerDeslocamentoMs();
  if (deslocamentoMs === 0) {
    return "tempo real";
  }
  const sinal = deslocamentoMs < 0 ? "-" : "+";
  const absolutoMs = Math.abs(deslocamentoMs);
  const dias = Math.floor(absolutoMs / UM_DIA_MS);
  const horas = Math.floor((absolutoMs % UM_DIA_MS) / UMA_HORA_MS);
  const minutos = Math.floor((absolutoMs % UMA_HORA_MS) / UM_MINUTO_MS);

  const partes = [];
  if (dias > 0) partes.push(`${dias}d`);
  if (horas > 0) partes.push(`${horas}h`);
  if (minutos > 0 || partes.length === 0) partes.push(`${minutos}min`);

  return `${sinal}${partes.join(" ")}`;
}
