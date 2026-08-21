# Activar la V8 neural en GitHub

## Archivos

Sube el contenido del ZIP conservando exactamente las carpetas. No elimines
`scripts/build_feature_store.py`, los scripts V5 ni los ledgers anteriores: la
V8 los usa como fuente, línea base y evidencia histórica.

La primera subida incluye código y documentación, pero todavía no incluye
pesos entrenados reales. Esos pesos deben surgir de tu propio workflow para que
el hash, las fechas y el dataset sean auténticos.

## Primera ejecución

1. Haz commit en `main`.
2. Abre **Actions**.
3. Selecciona **Actualizar datos e investigacion**.
4. Pulsa **Run workflow** sobre `main`.
5. Espera el check verde.
6. El bot hará un commit con:
   - `models/champion.json`, si una red califica;
   - `models/challengers/*.json`;
   - `models/neural_registry.json`;
   - `public/data/neural_lab.json`;
   - `public/data/neural_prediction_ledger.json`.
7. El workflow solicitará automáticamente el despliegue de GitHub Pages.

No necesitas crear secrets nuevos para entrenar la red. Continúan siendo
necesarios únicamente los proveedores que ya configuraste, como FRED, Gmail o
el Worker de Alpaca.

## Resultado esperado

En **Research Lab** aparecerá **Neural Model Observatory**. La primera ejecución
puede mostrar `Shadow challenger`. Eso no es un error: significa que la red aún
no demostró una mejora suficiente frente a la regresión logística. Forzar el
texto `Champion` manualmente invalidaría el experimento.

En ejecuciones posteriores:

- el challenger desde cero vuelve a entrenarse;
- el challenger warm-EWC continúa desde el Champion, si existe;
- se reevalúan modelos guardados;
- las predicciones anteriores maduran sin reescribirse;
- una promoción ocurre solo si todos los checks pasan.

## Frecuencia

- Cada 5 minutos: precios/alertas; no cambia pesos.
- Cada 20 minutos: noticias rápidas; no cambia pesos.
- Una vez al día: entrenamiento, calibración, evaluación y posible promoción.

Mantener esta separación evita que ruido intradía se convierta en memoria
permanente sin validación.
