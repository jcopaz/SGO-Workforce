# ADR-0006 | Atendimento de falha e catálogo RASF (Incremento 6)

## Contexto

Ao contrário do Incremento 5, o Incremento 6 tem uma regra **fechada e
inegociável** já registrada em
`docs/27_ALINHAMENTO_OFICIAL_SGO_WORKFORCE_v1_2.md`, seção 3.5:

> Um atendimento de falha não poderá ser encerrado sem os campos
> obrigatórios definidos para o MVP: número da nota, ativo, sintoma,
> causa, ação, observação técnica, horário final do atendimento.

`docs/09_ATENDIMENTO_FALHAS_RASF.md` detalha o fluxo (iniciar atendimento
→ registrar nota → selecionar ativo → selecionar sintoma → executar com
pausas/deslocamentos → informar causa/ação/observação ao encerrar) e
confirma os mesmos sete campos mínimos. O repositório já continha, em
`catalogos/`, os catálogos derivados do RASF (sintomas, sistemas, tipos de
solicitação, impactos, componentes causadores, três níveis 6M) extraídos
de uma planilha real de 3.986 registros — dados reais, não fabricados
nesta sessão.

## Decisão

1. **Atendimento de falha reaproveita a Atividade existente**, em vez de
   virar uma entidade paralela: `Atividade` ganhou um campo opcional
   `dados_falha: Optional[DadosFalha]`. Quando presente, a atividade *é*
   um atendimento de falha; quando `None`, comporta-se exatamente como
   antes. Isso reaproveita 100% da máquina de estados, das regras de
   pausa e da exclusão mútua com evento secundário já validadas nos
   Incrementos 1 e 5, sem duplicar lógica.
2. **`DadosFalha`** (`workforce_core/entities.py`): seis campos opcionais
   (`nota`, `ativo`, `sintoma`, `causa`, `acao`, `observacao`) — o sétimo
   campo obrigatório da seção 3.5 ("horário final") já é o `Atividade.fim`
   existente, não precisa de campo próprio.
3. **`MotorJornada.iniciar_atendimento_falha(quando)`**: chama
   `iniciar_atividade` internamente (herdando todas as suas validações) e
   anexa um `DadosFalha` vazio.
4. **`MotorJornada.registrar_dados_falha(**campos)`**: atualização
   parcial — só sobrescreve os campos explicitamente passados (não-`None`),
   permitindo preencher nota/ativo/sintoma no início e causa/ação/
   observação perto do fim, como o fluxo de `docs/09` descreve. Levanta
   `AtendimentoFalhaNaoAtivoError` se a atividade ativa não for um
   atendimento de falha (ou não houver atividade ativa).
5. **`encerrar_atividade` (já existente, inalterado na assinatura)**
   ganhou uma validação adicional: se `atividade.dados_falha is not None`,
   todos os seis campos devem estar preenchidos, senão levanta
   `AtendimentoFalhaCamposObrigatoriosError` listando exatamente quais
   estão faltando. **Não define quando** cada campo deve ser preenchido
   (a seção 3.5 só exige que estejam completos ao encerrar) — não inventa
   uma sequência obrigatória de telas.
6. **Catálogo RASF** (`workforce_storage/catalogo_rasf.py`): carrega os
   CSVs reais de `catalogos/` (mesmo formato em todos:
   `codigo_interno,valor,frequencia,ativo`, conforme
   `catalogos/dicionario_colunas_rasf.csv`). Preserva código e descrição
   originais e o status ativo/inativo, como pede
   `docs/09_ATENDIMENTO_FALHAS_RASF.md` ("Estratégia de catálogo"). Testado
   contra os arquivos reais do repositório (53 sintomas, 5 sistemas, 10
   tipos de solicitação, 4 impactos, 148 componentes causadores — números
   batem com `catalogos/README.md`).
7. **Sem validação cruzada obrigatória**: `registrar_dados_falha(sintoma=...)`
   aceita qualquer string — não valida contra o catálogo RASF carregado.
   Mesmo padrão já adotado para `Pausa.motivo` e `EventoSecundario.motivo`
   nos Incrementos 1 e 5: o motor de domínio não depende de I/O nem de um
   catálogo carregado: quem chama (UI ou uma camada de qualidade futura)
   decide se e como validar contra o catálogo.
8. **Persistência**: `FORMATO_VERSAO` sobe de 2 para 3
   (`workforce_storage/serializacao.py`), serializando `dados_falha` (ou
   `None`). Compatibilidade retroativa via `dados.get("dados_falha")` —
   arquivos v1/v2 continuam legíveis.

## Deliberadamente fora deste incremento

- **Campos recomendados** (sistema, componente causador, tipo/impacto,
  origem da atividade, OS relacionada, pendência, evidência, equipe): não
  implementados — a seção 3.5 só torna obrigatórios os sete campos
  mínimos; os recomendados ficam para quando forem priorizados.
- **Validação de sintoma/causa/ação contra o catálogo carregado**: o
  catálogo é carregável e consultável (`item_por_codigo`, `item_por_valor`,
  `apenas_ativos`), mas nada no motor hoje impede registrar um sintoma que
  não existe no catálogo. Ver item 7 acima.
- **Governança do catálogo** (versionamento, aprovação de novos valores,
  autoria de alteração): `docs/09` já deixa isso como responsabilidade da
  Eletroeletrônica, não deste incremento técnico.
- **Anexos/evidência fotográfica**: fora de escopo (campo recomendado, não
  obrigatório).
- **Paridade em JavaScript**: `interface_campo/` não expõe nenhuma tela de
  atendimento de falha ainda, então o motor JS não foi estendido — mesmo
  raciocínio do ADR-0004/ADR-0005 (sem UI exercitando a funcionalidade, sem
  risco imediato de divergência).

## Alternativas consideradas

- **Criar uma entidade `AtendimentoFalha` totalmente separada de
  `Atividade`**: rejeitado por duplicar toda a máquina de estados, as
  regras de pausa e a exclusão mútua com evento secundário sem necessidade
  — nada na seção 3.5 ou no doc09 exige uma entidade distinta, apenas
  campos adicionais obrigatórios ao encerrar.
- **Exigir nota/ativo/sintoma já no `iniciar_atendimento_falha`**:
  rejeitado — a seção 3.5 lista os sete campos juntos como exigência *de
  encerramento*, não de abertura; forçar isso na abertura seria inventar
  uma sequência de UX não especificada.
- **Validar sintoma contra o catálogo dentro do motor**: rejeitado para
  manter o motor de domínio livre de I/O e dependência de um catálogo
  carregado, mesmo padrão já usado para motivos de pausa/evento
  secundário.

## Validação operacional

Ainda não realizada quanto ao fluxo completo de atendimento em campo. A
regra dos sete campos obrigatórios já é uma decisão fechada (não uma
decisão nova desta sessão); a integração com o catálogo real e os campos
recomendados dependem de priorização futura.

## Data e responsáveis

- Data de registro: 2026-07-22.
- Registrado por: Claude Code, com autorização geral do responsável pelo
  produto (j.copaz@hotmail.com) para conduzir os incrementos do roadmap.
- Revisão pendente: responsável pelo produto (campos recomendados,
  validação cruzada com catálogo, governança do RASF) e paridade em
  JavaScript antes de expor esta função na interface de campo.
