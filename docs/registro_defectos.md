# Registro de defectos · Módulo de soborno académico

**Repositorio:** `osberdev/sprint-3-soborno-cutonala`, commit `cde923b`
**Fecha de registro:** 12 de noviembre de 2026
**Referencia de diseño:** autómata conceptual aprobado (estados q0–q6 y qS; reglas B1–B17)
**Corrección prevista:** durante la implementación del autómata nuevo

## Fuentes de evidencia

| Clave | Origen |
|---|---|
| F1 | Prueba manual en modo local (Ubuntu 24.04, Python 3.12.3), 12 de noviembre de 2026 |
| F2 | Prueba manual en modo Gemini (`google-genai` 3.3.0), 12 de noviembre de 2026 |
| F3 | Lectura del código. El comportamiento se deduce del código, pero no se ha observado en ejecución |
| F4 | Ejecución en el entorno de Claude, 30 de octubre de 2026 |

## Escala de severidad

- **Alta:** lleva a una ruta equivocada, omite protección o expone información.
- **Media:** confunde al usuario o contradice el diseño aprobado, sin llevar a una ruta peligrosa.
- **Baja:** afecta la presentación, la documentación o las pruebas.

---

## A. Defectos del programa

| ID | Defecto | Evidencia | Causa | Comportamiento esperado según el autómata | Severidad |
|---|---|---|---|---|---|
| D01 | "Ya pagué la inscripción y quiero saber mi calificación" se clasifica como posible soborno: (4,3), prioritaria, tres vías | F1 y F2, mensaje 5 | `sprint3_soborno.py:113–118`: el intercambio se presume (`intercambio or not excluye`) cuando aparecen a la vez una palabra de pago y una de evaluación | Permanecer en q1 Aclaración y preguntar si el pago estuvo condicionado a la calificación. Sin vínculo beneficio–ventaja, aplicar B5 (otro tema) | Alta |
| D02 | Una insinuación implícita ("un regalito ayudaría con la nota") no se reconoce como tal | F1 y F2, mensaje 6 | Léxico literal (`regalo` con límite de palabra no capta "regalito") y ningún concepto de lo implícito | B4: q1 ↺ con una pregunta dirigida a la insinuación. **Nota:** el estado resultante (1,1) con pregunta de aclaración ya coincide con el diseño; el defecto está en el reconocimiento y en la calidad de la pregunta, no en la ruta | Media |
| D03 | Tras una amenaza física, "Era broma, olvídalo" no cambia nada y se repite la misma respuesta urgente | F1 y F2, mensaje 8 | `conjunto` relee todo el historial (`sprint3_soborno.py:106–109`) y el estado solo puede subir (`max`) | qS solo se abandona con B17, cuando la persona confirma que está a salvo (1,0). No se ignora ni se borra la urgencia: se confirma | Alta |
| D04 | Se muestran al estudiante apartados de diseño interno (12.2 y 12.4) | F1 y F2, mensaje 6 | `chatbot_soborno.py:29` incluye el capítulo 12 en `CAPITULOS_INDEXADOS` | Recuperar solo contenido de orientación | Media |
| D05 | Tablas de Markdown (`\|---\|`) y negritas (`**`) aparecen sin procesar en los fragmentos | F1 y F2, mensajes 1, 2 y 7 | `mostrar` y `texto_visible` no limpian el formato al listar fragmentos | Texto limpio | Baja |
| D06 | Una consulta de antecedentes muestra la clasificación del caso anterior: (5,3) | F1, mensaje 9 | `mostrar` imprime las coordenadas en cualquier respuesta | B2 es un lazo informativo: no debe exhibir la urgencia del caso | Media |
| D07 | Gemini responde a la pregunta anterior al atender un mensaje nuevo ("Sobre dónde encontrar Primer Contacto…") | F2, mensaje 2 | `chatbot_soborno.py:229` envía los 3 últimos mensajes, incluidas las preguntas informativas ya respondidas | Enviar a Gemini solo los hechos del caso | Media |
| D08 | Gemini recita sus instrucciones aunque no vengan al caso: "la universidad no es un requisito previo…" (5 de 8 respuestas), "sin atribuir culpabilidad a la persona nombrada" sin que se nombre a nadie | F2, mensajes 2, 4, 5, 6 y 8 | El prompt de `explicar_con_gemini` tiene más de 15 reglas, casi todas en negativo | Mencionar solo lo pertinente al estado actual | Media |
| D09 | `test_pdf_separados_con_procedencia_y_pagina` falla con error si no está instalado `pypdf` | F1, paso 1 | `pruebas_faiss_y_casos.py:139` no comprueba antes la dependencia | Omitir la prueba, igual que la de FAISS | Baja |
| D10 | Documentación y configuración desalineadas: el README dice "siete pruebas" y hay 8; registra `google-genai` 2.29.0 y se instaló 3.3.0; el modelo por defecto es `gemini-3.8-flash` en un archivo y `gemini-3.5-flash-lite` en el otro; hay dos funciones de redacción con Gemini que se duplican | F1, F2 y F3 | Deriva entre versiones | Una sola configuración, documentada | Baja |
| D11 | Las preguntas informativas se guardan en el historial y afectan la clasificación posterior. Un mensaje que mezcla pregunta y relato solo se responde como pregunta, y el relato no se evalúa en ese turno | F3 | `sprint3_soborno.py:270`: se agrega al historial todo mensaje, incluidas las respuestas de preguntas frecuentes | B1 no aporta hechos al caso. Un mensaje mixto se atiende como pregunta y como relato | Media (por verificar) |
| D12 | La clasificación solo puede subir y nunca baja, mientras las vías se recalculan en cada mensaje. Resultado: (4,3) acompañado solo de la vía "personal" | F4 ("me dijeron que a otros también" después de un relato directo) | `max(x, …)` frente a `rutas` recalculadas desde cero en cada mensaje | El estado y sus vías se derivan de una única fuente | Media |
| D13 | No distingue a quien sufrió la exigencia de quien ofreció o entregó: no existen B15 ni q6 | F3 | No hay ningún campo de participación propia | B15 (1,0) lleva a q6 Asesoría jurídica | Alta (por verificar) |
| D14 | La vía legal se activa sola (y = 3) sin preguntar al usuario | F1 y F2, mensajes 3, 4, 5 y 7 | La rama de sospecha fija `y = 3` y las tres vías | B14 (1,0): se llega a q5 solo con la decisión de la persona | Alta |
| D15 | Una amenaza física se mezcla con la vía legal y el bot sigue haciendo preguntas ("dime en qué fecha…"). No distingue peligro actual de amenaza pasada | F1 y F2, mensaje 7 | (5,3) combina urgencia y capa legal; Gemini no recibe la instrucción de dejar de preguntar | B16 lleva a qS: atención inmediata y sin más preguntas. Una amenaza no actual va por B8 a q3 | Alta |
| D16 | El favoritismo se atiende dentro del módulo con vía UDG, y el acoso sexual no se detecta | F3 | `sprint3_soborno.py:136–140`; no hay léxico de acoso | B5: mencionar el tema del compañero que corresponde y no atenderlo | Media (por verificar) |
| D17 | No se detecta afectación personal: q2 solo se alcanza con la pregunta frecuente "me siento mal" | F3 | No hay regla equivalente a B6 | B6 lleva a q2 | Media (por verificar) |
| D18 | No hay movimientos laterales entre vías ni preguntas (1,0) en ninguna transición | F3 | El modelo de capas no tiene estados de orientación separados | B10–B13; (1,0) con repetición sin insistir | Media |
| D19 | El prompt de Gemini le ordena no mencionar Primer Contacto salvo pregunta o violencia. Contradice la consigna del Sprint 3 ("alineación del modelo del Gemini al programa del CUT, Primer Contacto") y el papel de q3 como estado central del nivel UDG | F3; se ve en F2, mensaje 2 | Regla del prompt en `explicar_con_gemini` | q3 orienta y canaliza en todo caso de soborno con intercambio explícito o amenaza | Media |

## B. Defectos del diagrama en Canva (`Automata_Soborno_Acad_mico_editable_1.pdf`, página 1)

| ID | Defecto | Corrección |
|---|---|---|
| G01 | Los estados de la columna 3 dicen **"q0 Inicial / Caso sin apoyo"** y **"q1 Aclaración / Hechos del caso"**. Son copias de la columna 1 | Arriba: **q6 Asesoría jurídica · Procuraduría Social**. Abajo: **q5 Autoridad externa · Fiscalía Anticorrupción** |
| G02 | Ningún estado tiene doble círculo, pero la leyenda dice "Doble círculo: orientación emitida" | Anillo interior en q2–q6 |
| G03 | Falta el lazo B8 en q3, y "en q3 se registra como hecho nuevo" no aparece | Agregar el lazo en el cuadrante superior izquierdo de q3 |
| G04 | B10 aparece sin "(1,0)"; la tabla de reglas sí lo indica | "B10 · Decide reportar (1,0)" |
| G05 | Errores de escritura y acentos: "autridad", "Afectacion", "Participacion", "Calificacion", "implicito", "Automata", "Metodologias", "Agil", "Bermudez" | Corregir |
| G06 | "Círculo con borde: fase de comprensión" ya no distingue nada, porque todos los círculos tienen borde | Restaurar "Círculo simple" y "Doble círculo" |

## C. Riesgos (no son defectos)

| ID | Riesgo | Estado |
|---|---|---|
| R01 | Con casos reales, en modo Gemini los relatos con nombres se envían a un servicio externo. Solo las consultas de antecedentes quedan excluidas | Seudonimización propuesta, no aprobada |
| R02 | El repositorio es público. `casos_docentes.local.json` está excluido de Git, pero conviene confirmarlo con `git check-ignore` antes de cada envío | Control vigente |

## D. Seguimiento

| Iteración | Defectos cerrados | Comprobación |
|---|---|---|
| 0 · Línea base | D09 | `pruebas_faiss_y_casos.py` termina en OK sin `pypdf` (prueba omitida) |
| 1 · Base segmentada | D04; D05 en tablas y negritas | `pruebas_conocimientos.py`: el capítulo 12 no se carga y ningún fragmento visible contiene `\|---` ni `**` |
| 2 · Autómata | D01, D02, D03, D06, D11–D18; D10 en parte (se eliminó la función duplicada de Gemini) | `escenarios_aceptacion.py` (20 escenarios) y `pruebas_automata.py` (conformidad con el diagrama y casos límite) |

Los defectos G01–G06 del diagrama no se corrigen en la imagen: la implementación sigue el autómata aprobado (q6 Asesoría jurídica, q5 Autoridad externa, aceptación en q2–q6, lazo B8 en q3, B10 con (1,0)).

## E. Defectos encontrados en la prueba manual de la iteración 2

| ID | Defecto | Evidencia | Corrección | Comprobación |
|---|---|---|---|---|
| D20 | La aclaración de q1 («¿estuvo condicionado…?») era texto libre: un «Si» no se interpretaba y el bot repetía la misma pregunta | Prueba manual, 12 nov 2026: «Ya pagué la inscripción…», «condiciondo por una calaificacion», «Si» | Aclaración C1 como pregunta de sí o no dentro de q1 (lazo B4): un «sí» confirma B7; un «no» la cierra sin clasificar soborno | `PruebasRegresionPruebaManual` en `pruebas_automata.py` |
| D21 | Los errores de escritura impedían reconocer el condicionamiento | Mismo turno | Corrección de palabras clave con `difflib` y patrón «condicionado a/por una calificación» | Mismo grupo de pruebas |
| D22 | La misma pregunta y la orientación del estado se repetían en cada turno sin información nueva | Mismo turno; también en q3 con «no sé» | Una reformulación y después se deja de preguntar; la orientación del estado solo se muestra al llegar a él | `test_no_repite_la_misma_pregunta_ni_insiste`, `test_un_no_se_en_primer_contacto_no_repite_la_orientacion` |
| D23 | «no entiendo» se leía como «no» | Prueba local posterior | Se interpreta como duda y se reformula la pregunta | `test_no_entiendo_no_es_un_no` |
| D24 | En q1 se recuperaban apartados ajenos al estado (7.1, 7.6) | Prueba manual | Recuperación por estado según el manifiesto: archivos del estado actual y del estado al que lleva la pregunta pendiente | `test_cada_estado_recupera_de_sus_archivos` |
| D25 | El mismo extracto («Dato recuperado» 5.1 o 14.1) se repetía en turnos seguidos aunque no hubiera nada nuevo | Prueba manual, 13 nov 2026 | Un turno sin regla ni pregunta informativa no busca fragmentos; el extracto solo aparece al llegar a una etapa o al responder una pregunta informativa, y nunca dos veces en la sesión | `test_extracto_no_se_repite_y_turno_sin_novedad_no_busca` |
| D26 | Un «si» sin pregunta pendiente devolvía siempre «Cuéntame qué pasó…» | Mismo día | Se avisa que no hay pregunta pendiente; una respuesta idéntica a la anterior se sustituye por una breve | `test_si_sin_pregunta_pendiente_no_repite_lo_mismo` |
| D27 | Los puntos de una lista se recuperaban sueltos («7. Información disponible…») | Mismo día | Los elementos consecutivos de una lista forman un solo fragmento | `test_listas_se_recuperan_completas` |
