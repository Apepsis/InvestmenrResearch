# Modelos persistentes V8

Esta carpeta contiene estado reproducible del sistema neural; no contiene
claves, posiciones personales ni credenciales.

- `champion.json`: pesos del Champion neural, únicamente después de aprobar
  todos los controles.
- `challengers/incumbent.json`: mejor challenger no promovido; se reevalúa en
  ejecuciones futuras.
- `challengers/runner_up.json`: segunda línea independiente.
- `archive/*.json`: antiguos champions disponibles para rollback o
  reconsideración.
- `neural_registry.json`: decisiones, hashes y cantidad total de ensayos.

Los JSON publican arquitectura, variables, medias y escalas, calibradores,
semillas, pesos y aproximación diagonal de Fisher. Esto permite reproducir el
forward pass. No edites estos archivos manualmente: el workflow diario los
genera y `scripts/validate_research_artifacts.py` comprueba que el modelo activo
coincida con el hash mostrado en la interfaz.
