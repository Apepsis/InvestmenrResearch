# Model Card — transparent-research-v4.0

## Uso previsto

Herramienta educativa de investigación financiera para horizontes aproximados
de 1 mes a 1 año. Compara evidencia y obliga a documentar tesis, riesgos e
invalidación. No ejecuta operaciones ni reemplaza asesoría financiera.

## Componentes

| Componente | Salida | Validación |
| --- | --- | --- |
| Score determinista | 0–100 y contribuciones | Reconciliación exacta |
| Modelo estadístico | Probabilidad de exceso positivo a 60 sesiones | Walk-forward y Brier score |
| Clasificador de noticias | Sentimiento, evento, relevancia y novedad | Línea base hasta completar etiquetas humanas |
| Modelo de riesgo | VaR, CVaR, beta, correlación y estrés | Pruebas unitarias y rangos |

## Datos de entrada

- Mercado diario: yfinance como conector de conveniencia.
- Fundamentales: SEC EDGAR cuando existe un concepto compatible; respaldo de
  datos de mercado claramente identificado.
- Macro: FRED.
- Noticias: Google News RSS más fuente original.
- Precio reciente: Alpaca Basic IEX mediante Cloudflare Worker.

## Métricas publicadas

- CAGR, Sharpe, Sortino, drawdown, volatilidad, hit rate, alpha y beta.
- Brier score, accuracy y reliability bins.
- Cobertura por activo y por proveedor.
- Matriz de confusión y F1 cuando el dataset humano de noticias sea suficiente.

## Riesgos de uso

- Extrapolación desde un universo pequeño.
- Sesgo de supervivencia.
- Revisiones posteriores de datos fundamentales.
- Cambios de régimen económico.
- Dependencias externas y disponibilidad desigual.
- Interpretar una probabilidad como certeza.

## Decisiones de seguridad

- Ninguna clave de Alpaca llega al navegador o a GitHub.
- Firestore separa documentos por UID.
- Los artefactos públicos no contienen posiciones personales.
- La validación rechaza cadenas compatibles con credenciales privadas.
