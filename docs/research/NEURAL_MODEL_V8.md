# Neural Model V8 — memoria, evaluación y promoción

## Objetivo

Estimar la probabilidad de que cada activo supere al SPY en 5, 20 y 60
sesiones. La V8 es un experimento probabilístico: no predice un precio exacto,
no ejecuta operaciones y no garantiza rentabilidad.

La primera red utiliza únicamente variables de mercado con historial
point-in-time. Noticias, fundamentales y macro continúan en el score explicable,
pero no se inyectan retrospectivamente a la red hasta construir archivos que
demuestren qué se conocía en cada fecha. Esa separación evita convertir datos
revisados hoy en una falsa señal histórica.

## Por qué una red pequeña

El universo actual contiene datos diarios de decenas de activos, no miles de
series históricas point-in-time. Una arquitectura grande aumentaría parámetros
y oportunidades de sobreajuste sin crear información nueva. Por eso la primera
versión utiliza un MLP multi-tarea `15 → 24 → 12 → 3`, implementado directamente
en NumPy. Tres inicializaciones forman un deep ensemble.

La elección se apoya en evidencia pública, no en una supuesta copia de un
sistema privado de Wall Street:

- Gu, Kelly y Xiu documentan que interacciones no lineales y ML pueden aportar
  a predicción de retornos, pero requieren validación rigurosa:
  <https://doi.org/10.1093/rfs/hhaa009>.
- Deep Ensembles ofrece una línea base práctica para incertidumbre predictiva:
  <https://doi.org/10.48550/arXiv.1612.01474>.
- Elastic Weight Consolidation motiva conservar parámetros importantes al
  continuar el aprendizaje:
  <https://doi.org/10.1073/pnas.1611835114>.
- Adaptive Conformal Inference estudia cobertura bajo cambio de distribución;
  esta V8 comienza con una banda split-conformal más simple y publica esa
  limitación: <https://doi.org/10.48550/arXiv.2106.00170>.
- El Deflated Sharpe Ratio advierte sobre selección entre muchos backtests:
  <https://doi.org/10.3905/jpm.2014.40.5.094>.
- La Probability of Backtest Overfitting formaliza el riesgo de escoger el
  mejor resultado entre múltiples variantes:
  <https://www.risk.net/journal-of-computational-finance/2471206/the-probability-of-backtest-overfitting>.

TFT, PatchTST y modelos fundacionales de series temporales son candidatos para
una etapa posterior, cuando exista más amplitud histórica point-in-time:

- Temporal Fusion Transformer: <https://doi.org/10.1016/j.ijforecast.2021.03.012>.
- PatchTST: <https://doi.org/10.48550/arXiv.2211.14730>.
- TimesFM: <https://research.google/pubs/a-decoder-only-foundation-model-for-time-series-forecasting/>.
- Chronos: <https://www.amazon.science/publications/chronos-learning-the-language-of-time-series>.

## Protocolo temporal

Las fechas se ordenan una sola vez:

1. Primer 60%: entrenamiento.
2. Embargo de 60 sesiones: impide que un target futuro cruce el corte.
3. Siguiente 20%: early stopping y calibración.
4. Segundo embargo de 60 sesiones.
5. Resto: shadow set que no participa en el ajuste.

Los tres objetivos se calculan en el feature store, pero nunca forman parte de
las variables de entrada. La normalización usa exclusivamente entrenamiento.

## Memoria persistente

Cada miembro guarda:

- matrices y sesgos de todas las capas;
- semilla;
- medias y escalas de normalización;
- calibradores Platt por horizonte;
- radio split-conformal;
- aproximación diagonal de Fisher;
- fechas, filas, variables, hiperparámetros, data hash y artifact hash.

El challenger `warm-ewc` comienza con pesos del Champion. Durante Adam agrega:

```text
gradiente_memoria = lambda × Fisher_diagonal × (peso_nuevo - peso_champion)
```

Esto reduce olvido catastrófico, pero no impide aprender. En paralelo se entrena
un challenger desde cero para detectar si la memoria se volvió una desventaja.

## Champion–Challenger

La referencia puede ser la regresión logística o un Champion neural ya
promovido. Cada challenger debe aprobar simultáneamente:

- muestra shadow mínima;
- mejora de Brier superior al umbral ajustado por cantidad de ensayos;
- menor log loss;
- ECE no peor por más de 0.01;
- mejora de Brier en al menos dos de tres horizontes;
- victoria en al menos la mitad de cuatro bloques temporales.

Un fallo conserva el Champion. La probabilidad ya publicada no cambia. El
mejor rechazado permanece en `models/challengers/` y los antiguos champions en
`models/archive/`; ambos pueden volver a competir con datos posteriores.

## Qué todavía falta

- Universo histórico point-in-time para reducir sesgo de supervivencia.
- Costos y performance económica específicos para las predicciones neuronales,
  además de Brier/log loss/ECE.
- Evaluación formal PBO/CSCV y DSR cuando existan suficientes bloques
  no solapados.
- Adaptive conformal online, en lugar de la banda split-conformal inicial.
- Comparación TFT/PatchTST solo después de aumentar datos y definir una línea
  base que justifique su costo.
