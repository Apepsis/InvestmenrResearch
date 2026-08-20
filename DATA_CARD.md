# Data Card

## Inventario

| Artefacto | Contenido | Público |
| --- | --- | --- |
| `market.json` | score, indicadores, macro, noticias y explicación | Sí |
| `backtest.json` | resultados fuera de muestra, splits y calibración | Sí |
| `risk_model.json` | retornos, correlaciones, beta y estrés | Sí |
| `event_studies.json` | retornos anormales por noticia | Sí |
| `research_manifest.json` | hashes, versión, cobertura y ejecución | Sí |
| Firestore | portafolio, vigilancia, diario y ajustes | No; por UID |
| `research_work/` | features y precios de trabajo | No; temporal |

## Política de fechas

- `generatedAt`: momento de construcción del artefacto.
- `asOf`: fecha efectiva del dato.
- Una fecha de publicación de noticia no implica que ya exista una ventana de
  retorno posterior.
- Los splits de backtesting publican fechas de entrenamiento, calibración y
  prueba.

## Datos faltantes

- Se representan como `null` o `No disponible`.
- Un valor anterior de FRED solo se reutiliza si conserva fecha, fuente y marca
  de dato desactualizado.
- Un proveedor puede fallar sin borrar resultados válidos de otros activos.
- El manifiesto publica cobertura y cantidad de errores no críticos.

## Privacidad

Los archivos públicos nunca deben incluir:

- correo del usuario;
- UID de Firebase;
- posiciones o diario personal;
- claves de Alpaca;
- cuentas de servicio;
- tokens de GitHub.

## Licencias y disponibilidad

El proyecto utiliza conectores gratuitos y públicos, pero cada proveedor puede
cambiar límites, cobertura o disponibilidad. La aplicación debe mostrar la
fuente y no representar un conector de conveniencia como fuente primaria.
