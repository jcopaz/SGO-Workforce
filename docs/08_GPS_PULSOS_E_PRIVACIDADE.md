# GPS, pulsos e privacidade

## Finalidade
Comprovar contexto de campo, estimar deslocamento e permanência, enriquecer mapas e apoiar auditoria operacional. Não é ferramenta de vigilância fora da jornada.

## Captura
Somente durante jornada ativa e conforme política institucional. Intervalo padrão deve ser configurável. Sugestão para piloto: 60 a 120 segundos, com adaptação futura por movimento/bateria.

## Campos
- UUID do pulso;
- jornada e usuário;
- timestamp do dispositivo;
- latitude/longitude;
- precisão em metros;
- velocidade e direção quando disponíveis;
- fonte;
- status do aplicativo;
- bateria opcional;
- timestamp de recebimento do servidor.

## Qualidade
Não inferir presença exata quando a precisão for ruim. Guardar a precisão original. Pontos impossíveis, saltos e velocidade incompatível devem ser marcados, não sobrescritos.

## Permanência
Agrupar pulsos próximos numa janela temporal, usando raio e tempo mínimos configuráveis. O resultado é uma inferência, sempre distinguida do evento declarado.

## Privacidade
- coletar apenas durante jornada;
- sinal visível de captura ativa;
- retenção definida;
- acesso por perfil;
- exportações com restrição;
- documentação transparente ao colaborador;
- avaliação prévia de LGPD e norma corporativa antes da produção.
