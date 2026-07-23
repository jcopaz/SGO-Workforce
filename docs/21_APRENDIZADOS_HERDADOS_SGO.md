# Aprendizados herdados do SGO

- Validar causa raiz com SQL/log e dado real.
- Segurança usa fail closed.
- Não criar filtros redundantes baseados em texto.
- Chave de conflito deve usar o identificador real.
- Datas operacionais não devem ser VARCHAR.
- Pin de dependências e Python suportado.
- Teste unitário não substitui teste em celular.
- Não remover widget stateful da árvore entre reruns.
- Offline exige idempotência e preservação do histórico sincronizado.
- Métrica zerada/anômala é alerta prioritário.
- Mudança grande vai para dev/homologação, nunca direto à produção.
