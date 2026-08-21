# Metodología de investigación reproducible

## Pregunta

¿Puede un modelo transparente estimar la probabilidad de que una acción supere
al SPY durante las siguientes 5, 20 o 60 sesiones sin utilizar información
futura, publicar la predicción antes del resultado y controlar el riesgo?

La aplicación separa dos salidas:

1. **Score de investigación:** síntesis explicable de técnico, fundamentales,
   noticias, macro y riesgo. No se presenta como probabilidad.
2. **Probabilidad estadística:** salida de una regresión logística evaluada
   fuera de muestra. Su calibración se mide con Brier score y reliability bins.

## Score explicable

El score utiliza una base neutral de 50. Para cada bloque `i`:

```text
contribución_i = (score_i - 50) × peso_i
score_total = 50 + suma(contribución_i)
```

Pesos versionados:

| Bloque | Peso |
| --- | ---: |
| Técnico | 25% |
| Fundamental | 30% |
| Noticias | 15% |
| Macro | 15% |
| Riesgo | 15% |

La interfaz publica el valor original, normalización, peso, contribución,
fórmula, fuente, fecha y estado de cada bloque. El simulador personal de pesos
no reemplaza el score oficial ni modifica el experimento auditado.

## Feature store

`scripts/build_feature_store.py` crea variables conocidas en cada fecha:

- retornos de 5, 20 y 60 sesiones;
- distancia a SMA 50 y SMA 200;
- RSI 14;
- volatilidad de 20 y 60 sesiones;
- drawdown de 252 sesiones;
- z-score de volumen de 20 sesiones;
- retorno del SPY de 20 y 60 sesiones;
- distancia de SPY a SMA 200 y volatilidad de SPY a 60 sesiones;
- beta móvil de 60 sesiones.

El objetivo se calcula aparte:

```text
exceso_futuro_h = retorno_activo_futuro_h - retorno_SPY_futuro_h
label_h = 1 si exceso_futuro_h > 0; en otro caso 0
h ∈ {5, 20, 60}
```

Las columnas futuras están prohibidas dentro de la matriz de features y existe
una prueba automática que verifica esa separación.

## Validación walk-forward

Para cada año de prueba:

1. Entrenar con años anteriores.
2. Reservar la parte final del entrenamiento para calibración.
3. Ajustar normalización únicamente con el conjunto de entrenamiento.
4. Calibrar probabilidades sin observar el año de prueba.
5. Evaluar el año siguiente.
6. Guardar todas las fechas y tamaños del split.

El modelo estadístico es una regresión logística L2 implementada en
`scripts/research_core.py`. La implementación es intencionalmente pequeña para
que sus gradientes, regularización y normalización puedan inspeccionarse.

## Estrategias comparadas

- Comprar y mantener SPY.
- Regla técnica determinista.
- Score heurístico de mercado y riesgo.
- Regresión logística L2 calibrada temporalmente.
- Challenger estadístico con control de riesgo.

Cada 60 sesiones las tres acciones con mayor ranking se ponderan por igual. Se
descuentan 10 puntos básicos por rebalanceo. Se publican CAGR, Sharpe, Sortino,
drawdown máximo, volatilidad, hit rate, alpha y beta.

El challenger selecciona hasta cinco activos, limita cada peso a 20%, apunta a
12% de volatilidad anual, usa un proxy de CVaR diario de 2% y reduce la
exposición máxima a 35% cuando SPY está bajo su SMA 200. El resto permanece en
efectivo con retorno asumido de 0%. Estas reglas son fijas y se evalúan con el
mismo periodo fuera de muestra.

## Ledger de predicciones

Cada ejecución diaria publica una predicción por activo y horizonte. ID, fecha,
probabilidad, banda empírica, precio inicial, versión y hash no pueden cambiar.
Cuando existen exactamente 5, 20 o 60 observaciones posteriores, el sistema
agrega retorno del activo, retorno de SPY, exceso y acierto. No vuelve a entrenar
el pasado para sustituir esa predicción.

La banda de incertidumbre combina error de calibración y tamaño de la muestra;
es una medida empírica para comunicar incertidumbre, no un intervalo formal con
cobertura garantizada.

## Champion–challenger y drift

El challenger solo puede convertirse en champion si mejora Sharpe al menos
0.05, reduce drawdown al menos 5 puntos porcentuales, mantiene CAGR dentro de 2
puntos y tiene al menos 12 observaciones. Debe cumplir todo durante tres
ejecuciones diarias distintas. Las predicciones anteriores conservan su versión.

El monitoreo publica cobertura, antigüedad de datos, desplazamientos
estandarizados de features y Brier/accuracy realizados cuando existen al menos
30 predicciones maduras.

## Noticias y event study

El pipeline:

1. recupera titulares;
2. elimina casi duplicados mediante similitud de Jaccard;
3. confirma coincidencia de entidad;
4. clasifica evento y sentimiento;
5. estima relevancia y novedad;
6. calcula retorno anormal contra SPY en 1, 5 y 20 sesiones.

Una ventana futura inexistente permanece como `pending`. El sistema no la
rellena con cero ni inventa un resultado.

El clasificador léxico es una línea base. `data/news_labels.csv` y
`scripts/evaluate_news_models.py` permiten comparar esa línea base contra TF-IDF
más regresión logística. FinBERT queda explícitamente como `not_evaluated`
hasta documentar pesos, versión, entorno y dataset humano.

## Riesgo

El navegador combina las posiciones privadas del usuario con un modelo público
de retornos. Así las posiciones no salen de Firebase ni se incluyen en GitHub.

- VaR 95%: percentil empírico 5% de retornos diarios.
- CVaR 95%: promedio de retornos inferiores o iguales al VaR.
- Beta: covarianza con SPY dividida por varianza de SPY.
- Correlación: Pearson con observaciones pareadas.
- Drawdown: mayor caída de capital desde un máximo previo.

Los escenarios son sensibilidades definidas, no predicciones.

## Reproducibilidad

Cada ejecución publica:

- Run ID;
- versión del modelo;
- commit de Git;
- SHA-256 de cada artefacto;
- hash combinado del dataset;
- cobertura;
- errores no críticos;
- cantidad de pruebas aprobadas;
- duración.

## Limitaciones

- El universo de 32 acciones más SPY fue seleccionado hoy y mantiene riesgo de supervivencia.
- Los fundamentales históricos point-in-time aún no participan en el modelo
  retrospectivo.
- Google News RSS no es un archivo completo de noticias históricas.
- IEX puede diferir del mercado consolidado.
- Un backtest favorable no establece causalidad ni garantiza rentabilidad.
