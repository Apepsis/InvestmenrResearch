# Protocolo de etiquetado de noticias

Este archivo evita presentar un modelo de NLP como válido antes de medirlo.
Completa `news_labels.csv` con al menos 200 titulares y conserva también los
casos ambiguos.

## Campos

- `title`: titular exacto.
- `label`: `positive`, `neutral` o `negative` respecto a la empresa.
- `event_type`: `resultados`, `regulación`, `producto`, `litigio`,
  `administración`, `competencia`, `estratégico` o `mercado`.
- `relevance`: número entre 0 y 1 que indica cuánto se refiere el titular a la
  empresa analizada.
- `reviewer`: iniciales de quien etiquetó.
- `notes`: justificación breve para casos difíciles.

## Reglas

1. Etiqueta el efecto descrito por el titular, no el movimiento posterior de la
   acción.
2. No leas el retorno posterior antes de asignar la clase.
3. Deduplica titulares casi idénticos, pero conserva fuentes contradictorias.
4. Revisa una muestra dos veces y registra desacuerdos.
5. No declares ganador a FinBERT, regresión o lexicón hasta comparar F1 macro,
   precisión, recall y matriz de confusión sobre ejemplos no usados al entrenar.
