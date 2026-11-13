# Pruebas manuales del 12 y 13 de noviembre de 2026

Ejecutadas por el autor en Ubuntu 24.04 (WSL), Python 3.12.3, `google-genai` 3.3.0, `faiss-cpu` 1.16.0, sobre la rama `automata-v2`. El autor envió capturas de pantalla de cada sesión; esta tabla resume lo observado. Algunas sesiones usaron nombres de docentes; no se transcriben aquí. Los defectos citados se describen en `docs/registro_defectos.md`.

| Fecha y hora | Modo | Qué se probó | Resultado | Defectos encontrados |
|---|---|---|---|---|
| 12 nov | Local y `--gemini` (versión anterior al autómata) | Guion de nueve mensajes: pregunta institucional, rumor, exigencia, amenaza, pago ordinario, insinuación, amenaza física, retractación, antecedentes | Línea base del registro | D01–D19 |
| 12 nov | Local (autómata nuevo, iteración 2) | Aclaración con «Si», errores de escritura, «no entiendo», repeticiones | Bucle en la aclaración y respuestas repetidas | D20–D27 |
| 13 nov, 01:19 | Local | Pago bajo presión → q2 → B15, «no se», «sii», antecedentes, peligro actual, a salvo | q2 correcto; «sii» no se reconocía | D28–D32; D33 (salida de Seguridad) decidido: opción A |
| 13 nov, 01:26 | Local | «no» a B15 y «ok gracis» | Se queda en q2 sin insistir | Confirma D29–D32 |
| 13 nov, 01:30 | Local | Mismo guion completo hasta q6, peligro y «Ya estoy a salvo» | Retoma en q6 con B17, B6, B15 | Confirma D33; D35–D37 |
| 13 nov, 08:01 | `--gemini` | Pregunta informativa, relato con nombre y monto, pregunta sin dato, relato coloquial | El texto de Gemini no contiene el nombre ni el monto (no los recibe); los datos citados están en la investigación | D38–D41 |
| 13 nov, 08:09 | `--gemini` | «donde esta primer co», insinuación, «despachan los sabados?» | Dos tiempos agotados; redacción sin eco de instrucciones | D43–D46 |
| 13 nov, 08:17 | `--gemini --extractor-gemini` | Pregunta por ubicación y relato con «billetes» | El extractor real añade beneficio, exigencia, nexo y ventaja con cita; la verificación descarta una redacción por un falso positivo | D48–D50 |
| 13 nov, 08:46 | Local | Pago condicionado presentado como comida para animales | q3 por B7 correcto | D53–D54 |
| 13 nov, 09:00 | `--reindexar-faiss` | Índice sobre `conocimientos/` con embeddings reales | 97 fragmentos de orientación y 8 de relatos; aviso para retomar el caso guardado | — |
| 13 nov, 09:19 | Local | Encargada de Primer Contacto y relato en q3 | Solo 6.2; en q3, 5.1 (artículo 21.1), 7.3 y 7.6 | Confirma D34 |
| 13 nov, 09:20 | `--faiss` | Mismos dos mensajes | Filtro correcto; en q3 el artículo 21.1 no aparecía | D56 |
| 13 nov, 09:32 | `--faiss` | Mismos dos mensajes | En q3: 5.1 (artículo 21.1), 7.3, 5.2 | Confirma D56 |

Estas pruebas comprueban el comportamiento del programa en casos concretos; no validan jurídicamente el contenido.
