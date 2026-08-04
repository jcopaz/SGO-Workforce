// Captura de GPS no preenchimento do atendimento de falha (D2 do roteiro
// combinado com o responsavel pelo produto, apos o ADR-0021).
//
// Best-effort, nunca trava o app: API ausente, permissao negada, timeout
// ou qualquer outro erro sempre resolvem para null - quem chama decide
// como avisar o colaborador, mas o preenchimento/encerramento do
// atendimento de falha nunca depende disto (regra de ouro 7/8 do
// CLAUDE.md, decisao explicita do responsavel pelo produto).

const TIMEOUT_PADRAO_MS = 10000;

// `opcoes.geolocationImpl` permite substituir `navigator.geolocation` em
// teste (Node nao tem essa API) - por padrao usa a API real do navegador.
export function capturarPosicaoAtual(opcoes = {}) {
  const {
    geolocationImpl = typeof navigator !== "undefined" ? navigator.geolocation : undefined,
    timeoutMs = TIMEOUT_PADRAO_MS,
  } = opcoes;

  if (!geolocationImpl) {
    return Promise.resolve(null);
  }

  return new Promise((resolve) => {
    geolocationImpl.getCurrentPosition(
      (posicao) => {
        resolve({
          latitude: posicao.coords.latitude,
          longitude: posicao.coords.longitude,
          precisaoMetros: posicao.coords.accuracy,
          capturadoEm: new Date(posicao.timestamp),
          // Nem todo navegador/dispositivo fornece velocidade/direcao -
          // ficam null quando ausentes, e habilitam do lado do dominio
          // (qualidade_gps.avaliar_pulso) uma checagem de velocidade
          // reportada pelo proprio aparelho, nunca calculada aqui.
          velocidadeMetrosSegundo: posicao.coords.speed ?? null,
          direcaoGraus: posicao.coords.heading ?? null,
        });
      },
      () => resolve(null),
      { enableHighAccuracy: true, timeout: timeoutMs, maximumAge: 0 }
    );
  });
}

// Captura periodica em segundo plano (Fase 2 da captacao de geolocalizacao,
// ADR-0043: 1 pulso por minuto durante a jornada ativa). Best-effort igual a
// capturarPosicaoAtual: uma falha isolada nunca interrompe o intervalo, so
// deixa de chamar `aoCapturar` naquele ciclo (a lacuna fica visivel no
// backend pela ausencia do pulso, nunca precisa travar nada aqui - regra de
// ouro 8 do CLAUDE.md).
export function iniciarCapturaPeriodica(aoCapturar, opcoes = {}) {
  const { intervaloMs = 60000, ...opcoesCaptura } = opcoes;
  return setInterval(async () => {
    const posicao = await capturarPosicaoAtual(opcoesCaptura);
    if (posicao) {
      aoCapturar(posicao);
    }
  }, intervaloMs);
}

export function pararCapturaPeriodica(idIntervalo) {
  if (idIntervalo != null) {
    clearInterval(idIntervalo);
  }
}
