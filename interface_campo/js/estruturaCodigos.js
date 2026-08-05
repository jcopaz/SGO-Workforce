// Agrupamento visual dos 23 codigos do Relatorio 1 em 3 blocos
// operacionais (pedido do responsavel pelo produto em 2026-08-04,
// ADR-0050): reduz a carga cognitiva de escolher entre 23 codigos numa
// lista so, organizando pela jornada operacional do eletricista -
// Apoio e Preparacao -> Execucao -> Interrupcoes -> volta pra Execucao.
//
// So agrupamento VISUAL - nunca um catalogo. As descricoes de cada
// codigo continuam vindo do catalogo dinamico (backend, com fallback
// offline - ver catalogoMotivos.js), nunca hardcoded aqui; isto aqui so
// decide EM QUAL BLOCO cada codigo aparece. Nao muda nenhum
// comportamento do motor de dominio (motorJornada.js).
//
// Duas reconciliacoes entre a especificacao original e o motor de
// dominio real (documentadas no ADR-0050):
// - EE17 (Manutencao Programada) e EE21 (Atendimento de Falha) nao sao
//   codigos "soltos" - sao o resultado de como uma Atividade e iniciada
//   (motor.iniciarAtividade/iniciarAtendimentoFalha). Ficam FORA da
//   lista de codigos deste modulo; app.js injeta os dois como itens
//   especiais no bloco Execucao (ver ITENS_EXTRAS_EXECUCAO em app.js).
// - EE23 (Manutencao Nao Concluida) tambem nao e selecionavel para
//   INICIAR nada - so existe como desfecho de ENCERRAMENTO de uma
//   atividade ja em andamento (botao "Atividade nao concluida"). Nao
//   aparece em bloco nenhum aqui.
// - EE22 (Treinamento) nao apareceu em nenhum bloco na especificacao
//   original recebida - e tipo_registro=pausa, mesma familia de EE02/
//   EE11 (SMS/Refeicao/Consulta a documentacao), adicionado em
//   Interrupcoes > Pausas.

export const BLOCO_APOIO_PREPARACAO = "apoio_preparacao";
export const BLOCO_EXECUCAO = "execucao";
export const BLOCO_INTERRUPCOES = "interrupcoes";

export const ESTRUTURA_BLOCOS = [
  {
    id: BLOCO_APOIO_PREPARACAO,
    titulo: "1. Apoio e Preparação",
    emoji: "🔵",
    codigos: ["EE01", "EE20", "EE07", "EE08", "EE12", "EE13", "EE14", "EE18", "EE19", "EE15"],
  },
  {
    id: BLOCO_EXECUCAO,
    titulo: "2. Execução",
    emoji: "🟢",
    // EE17/EE21 sao pontos de entrada especiais (iniciar atividade/
    // atendimento de falha) - injetados por quem chama via
    // `itensExtrasPorBloco`, nao vem do catalogo dinamico. EE16
    // (Desmontar atividade) e o unico codigo solto de verdade aqui.
    codigos: ["EE16"],
  },
  {
    id: BLOCO_INTERRUPCOES,
    titulo: "3. Interrupções",
    emoji: "🔴",
    subgrupos: [
      { titulo: "Esperas", codigos: ["EE03", "EE04", "EE05", "EE06", "EE09", "EE10"] },
      { titulo: "Pausas", codigos: ["EE02", "EE11", "EE22"] },
    ],
  },
];

function todosCodigosClassificados() {
  const codigos = new Set();
  for (const bloco of ESTRUTURA_BLOCOS) {
    for (const codigo of bloco.codigos ?? []) codigos.add(codigo);
    for (const subgrupo of bloco.subgrupos ?? []) {
      for (const codigo of subgrupo.codigos) codigos.add(codigo);
    }
  }
  return codigos;
}

// Filtra a estrutura de blocos para conter so os codigos presentes em
// `motivosDisponiveis` (lista de {codigo, descricao, ...} do catalogo
// dinamico) - cada contexto (jornada solta vs pausa aninhada numa
// atividade) so oferece um subconjunto dos 23 codigos (o motor de
// dominio decide isso, nunca este modulo). Blocos/subgrupos que ficam
// vazios nao aparecem na saida.
//
// `itensExtrasPorBloco` (opcional, ex.: `{ execucao: [...] }`) injeta
// itens que nao vem do catalogo (as sentinelas de iniciar atividade/
// atendimento de falha) no comeco do bloco indicado.
//
// Codigo presente em `motivosDisponiveis` mas nao classificado em nenhum
// bloco (ex.: catalogo ganhou um codigo novo que este arquivo ainda nao
// conhece) cai num bloco "Outros" no final - nunca some silenciosamente,
// rede de seguranca contra esquecer um codigo (ja aconteceu uma vez com
// o EE22 na especificacao original).
export function agruparCodigosDisponiveis(motivosDisponiveis, itensExtrasPorBloco = {}) {
  const porCodigo = new Map(motivosDisponiveis.map((motivo) => [motivo.codigo, motivo]));
  const blocos = [];

  for (const blocoOriginal of ESTRUTURA_BLOCOS) {
    const extras = itensExtrasPorBloco[blocoOriginal.id] ?? [];
    const bloco = { id: blocoOriginal.id, titulo: blocoOriginal.titulo, emoji: blocoOriginal.emoji };

    if (blocoOriginal.codigos) {
      const doCatalogo = blocoOriginal.codigos.map((c) => porCodigo.get(c)).filter(Boolean);
      bloco.itens = [...extras, ...doCatalogo];
      if (bloco.itens.length > 0) blocos.push(bloco);
    } else if (blocoOriginal.subgrupos) {
      bloco.subgrupos = blocoOriginal.subgrupos
        .map((subgrupo) => ({
          titulo: subgrupo.titulo,
          itens: subgrupo.codigos.map((c) => porCodigo.get(c)).filter(Boolean),
        }))
        .filter((subgrupo) => subgrupo.itens.length > 0);
      if (bloco.subgrupos.length > 0) blocos.push(bloco);
    }
  }

  const classificados = todosCodigosClassificados();
  const orfaos = motivosDisponiveis.filter((motivo) => !classificados.has(motivo.codigo));
  if (orfaos.length > 0) {
    blocos.push({ id: "outros", titulo: "Outros", emoji: "⚪", itens: orfaos });
  }

  return blocos;
}
