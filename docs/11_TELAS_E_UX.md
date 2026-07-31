# Telas e UX

## Captura de campo
- Login.
- Estado atual da jornada.
- Botão grande Iniciar Jornada.
- Cartões: Atividade, Falha, Pausa, Deslocamento, Apoio.
- Cronômetro apenas informativo.
- Ação principal sempre visível.
- Fila offline e status de GPS visíveis.

**Implementado no ADR-0030**: a tela "jornada aberta, sem nada em
andamento" usa uma lista única (não cartões separados) com todas as
ações - Iniciar atividade, Atendimento de falha, e os 20 códigos de
pausa/deslocamento/espera/apoio - e um único botão "Iniciar" que vira
"Encerrar" enquanto algo está em andamento, voltando para a mesma lista
ao encerrar. "Encerrar jornada" fica fora da lista, como ação terminal
separada.

## Encerramento de falha
Formulário progressivo com nota, ativo, sintoma, causa, ação e observação. Campos catalogados com busca. Bloqueio claro e explicativo quando faltar informação.

## Painel
- Visão Geral.
- Jornada e HH.
- Falhas/RASF.
- Mapa.
- Capacidade PCM.
- Exportações.
- Administração.

## Regras de UX
- poucos toques;
- fontes e botões adequados ao celular;
- não depender de cor isoladamente;
- confirmar transições destrutivas;
- nunca perder formulário em rerun;
- salvar rascunho local;
- indicar offline, pendente e sincronizado.
