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
| R01 | Con casos reales, en modo Gemini los relatos con nombres se envían a un servicio externo. Solo las consultas de antecedentes quedan excluidas | Reducido en la iteración 4: `--gemini` ya no envía el texto de los mensajes, solo hechos en frases neutras. `--extractor-gemini` sí envía cada mensaje (con `store=False`) y es opcional. Seudonimización propuesta, no aprobada |
| R02 | El repositorio es público. `casos_docentes.local.json` está excluido de Git, pero conviene confirmarlo con `git check-ignore` antes de cada envío | Control vigente |

## D. Seguimiento

| Iteración | Defectos cerrados | Comprobación |
|---|---|---|
| 0 · Línea base | D09 | `pruebas_faiss_y_casos.py` termina en OK sin `pypdf` (prueba omitida) |
| 1 · Base segmentada | D04; D05 en tablas y negritas | `pruebas_conocimientos.py`: el capítulo 12 no se carga y ningún fragmento visible contiene `\|---` ni `**` |
| 2 · Autómata | D01, D02, D03, D06, D11–D18; D10 en parte (se eliminó la función duplicada de Gemini) | `escenarios_aceptacion.py` (20 escenarios) y `pruebas_automata.py` (conformidad con el diagrama y casos límite) |
| 3 · Pruebas manuales (12–13 nov) | D20–D37; D33 con la opción A aprobada | `PruebasRegresionPruebaManual*` en `pruebas_automata.py`, escenarios G9b y G11, `pruebas_conocimientos.py` |
| 4 · Gemini | D07, D08, D19; D10 en la configuración del modelo y la versión de `google-genai` (el conteo de pruebas del README queda para la iteración 7) | `pruebas_gemini.py`: qué se envía, instrucción en positivo, siete datos inventados que regresan a la respuesta local, pregunta informativa trampa, extractor con citas y fallos del servicio |

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
| D28 | «sii» (letra repetida) no se reconocía como «sí»: la decisión B15 no se resolvía y el caso no llegaba a q6 | Prueba manual, 13 nov 2026: «Le di 500 pesos…», «no se», «sii» | Las letras repetidas se reducen antes de interpretar la respuesta («siii» → «si», «noo» → «no»); se aceptan «sip», «simón», «nel», «nop» | `test_si_alargado_responde_la_decision`, `test_variantes_de_si_y_no` |
| D29 | En q2, un «no» a B15 volvía a preguntar B15 en la misma respuesta; el siguiente «ok gracias» se leía como «sí» y llevaba a q6 sin consentimiento | Reproducción local del mismo escenario | Cada decisión de q2 se pregunta una sola vez | `test_un_no_a_b15_no_se_vuelve_a_preguntar` |
| D30 | «ok», «va», «sale» contaban como «sí» aunque fueran parte de otra frase («ok gracias», «va a reprobarme») | Misma reproducción | Esas palabras solo valen como «sí» cuando son el mensaje completo | `test_variantes_de_si_y_no` |
| D31 | Un mensaje que no es sí ni no, con una decisión pendiente, devolvía «RESPUESTA:» vacía seguida de la pregunta, sin límite de intentos (el límite solo existía para C1) | Prueba manual, turno «sii» | Cuenta como intento en cualquier pregunta (1,0): primero recuerda que basta con sí o no, después registra la decisión como «desconocido» y no insiste; si el mensaje trae hechos, avisa que quedan anotados | `test_respuesta_no_reconocida_no_deja_la_respuesta_vacia_ni_insiste` |
| D32 | Tras un «no» a cualquier decisión, cada turno sin novedad alternaba «De acuerdo…» con «Sigo atento… cuéntame qué pasó», aunque el caso ya estuviera relatado | Misma reproducción | «De acuerdo» solo acompaña al turno en que se respondió; fuera de q0 y q1 la respuesta breve ya no pide el relato | `test_un_no_a_b15_no_se_vuelve_a_preguntar` |
| D33 | Al salir de qS (B17) el caso vuelve a q1 y pide «cuéntame qué pasó», aunque la ficha ya tiene el relato y el caso había llegado a q2 o q6 | Prueba manual, turno «Ya estoy a salvo.» | Opción A, aprobada el 13 nov 2026: B17 entra a q1, como marca el diagrama, y en el mismo turno el caso recorre de nuevo las flechas que ya había tomado desde q1 (se guardan sin lazos ni qS). Las decisiones respondidas no se repiten; una pregunta sin responder se vuelve a hacer. Sin caso previo, se queda en q1 y pide el relato. Retomar no muestra extracto. El escenario aprobado G9b cambia de q1 a q3 por esta decisión; se agrega G11 | `test_salir_de_seguridad_*`, `test_el_camino_retomado_usa_solo_flechas_del_diagrama`, `test_retomar_el_caso_tras_seguridad_no_agrega_extracto`, escenarios G9b y G11 |
| D34 | Una pregunta informativa recupera fragmentos de todo el corpus: «¿Quién es la encargada de Primer Contacto?» trajo 8.2 (matriz de prioridad, amenazas) | Prueba manual, primer turno | Pendiente: filtrar por la intención de la pregunta (iteración 6, junto con FAISS) | — |
| D35 | Texto que describe el diseño del prototipo podía mostrarse al estudiante o enviarse a Gemini: 8.2 («Esta matriz organiza la orientación del prototipo»), 8.3 («el sistema puede sugerir…»), 2.3, 5.2, 14.1 | Prueba manual, 13 nov 2026 (fragmentos 8.2 y 8.3) | Opción (b), aprobada el 13 nov 2026: los archivos siguen íntegros; al indexar se omite el apartado 8.2 y las oraciones listadas en `manifiesto.json` → `no_indexar`. Las frases que informan un límite del chatbot al estudiante («no puede certificarlo como prueba», «no puede negociarlas») se conservan. Un filtro por palabras sueltas («prototipo», «sistema») se descartó porque eliminaba orientación válida de 4.2, 5.2, 6.2 y 7.5 | `test_texto_de_diseno_del_prototipo_no_se_indexa`, `test_lo_que_orienta_se_conserva_junto_al_diseno` |
| D36 | q5 y q6 mostraban «fase 3/3 Autoridad externa», el mismo nombre del estado q5; la asesoría jurídica no es una autoridad | Misma prueba | La fase 3 se llama «Orientar fuera de la UdeG» | `test_estados_aceptacion_y_terminales` |
| D37 | El «Dato recuperado» podía repetir lo que ya decía la respuesta (4.3 en q2; 6.2 tras la pregunta por la encargada) | Misma prueba | Solo se muestra un extracto si al menos la mitad de sus palabras de contenido no están en la respuesta; el turno que retoma el caso tras Seguridad no busca fragmentos | `test_extracto_que_repite_la_respuesta_no_se_muestra`, `test_retomar_el_caso_tras_seguridad_no_agrega_extracto` |
| D38 | Una pregunta que la base no responde («atienden los sabados?») se trataba como relato en q0 (B3) o como respuesta inválida a la pregunta pendiente («Para continuar necesito un sí o un no») | Prueba con Gemini, 13 nov 2026 | Una pregunta sin hechos ni intención reconocida recibe «No tengo información oficial sobre eso…» (regla del profesor), no abre un caso y no cuenta como intento | `PruebasPreguntaSinDato` |
| D39 | Gemini copiaba las instrucciones en la respuesta: «El programa añade después, por separado, la pregunta del turno», «esta orientación no es una denuncia ni una decisión jurídica», «En esta etapa de primer contacto» | Misma prueba, turnos 1, 2 y 4 | Instrucciones reescritas (los hechos guían, no se repiten; la tarjeta es interna; el campo «etapa» pasa a «estado_interno»); las oraciones que repiten instrucciones o la tarjeta se omiten antes de mostrar la redacción | `test_eco_de_las_instrucciones_se_omite`, `test_la_orientacion_local_no_se_confunde_con_un_eco` |
| D40 | Gemini redactaba también turnos sin novedad, repitiendo la orientación del estado; en una pregunta informativa hablaba de «lo que relatas» | Misma prueba, turnos 1 y 3 | Gemini solo redacta turnos con una regla o una pregunta informativa; la tarjeta indica la pregunta y la instrucción pide responderla | `test_gemini_solo_redacta_turnos_con_regla_o_pregunta_informativa` |
| D41 | Con `--extractor-gemini`, un turno sin hechos adicionales no mostraba nada: no se distinguía si el extractor se consultó | Misma prueba, turno 4 | Se imprime «EXTRACTOR GEMINI: respondió sin hechos adicionales» | `test_se_informa_cuando_el_extractor_no_encuentra_hechos` |
| D42 | Una pregunta hipotética con hechos («¿Y si me amenaza con reprobarme?») se registra como hecho del caso (B8) | Revisión de D38 | Pendiente: el condicional no se distingue de lo ocurrido | — |
| D43 | Gemini agotó el tiempo dos veces en una sesión (12 s) y el aviso salía en inglés («Request timed out…») | Segunda prueba con Gemini, 13 nov 2026 | Espera de 20 s; los fallos del servicio se describen en español («sin respuesta en 20 s», «cuota temporal agotada»), también en el extractor | `test_fallos_del_servicio_se_describen_en_espanol`, `test_fallo_del_extractor_se_describe_en_espanol` |
| D44 | Si el turno solo tenía la pregunta (reformulación de C1), «RESPUESTA:» quedaba vacía y la pregunta pasaba a la línea siguiente | Misma prueba | Sin texto previo, la pregunta ocupa la primera línea | `test_pregunta_sin_texto_previo_va_en_la_primera_linea` |
| D45 | «donde esta primer co» y «donde encuentro contacto uno» no se reconocían como pregunta por Primer Contacto; con D38 recibían «No tengo información oficial», aunque el dato existe. «en primer contacto, atienden los sabados?» tampoco | Misma prueba | Formas incompletas («primer co…», «contacto uno») se leen como Primer Contacto; «atienden», «despachan», «abren», «días» cuentan como pregunta por la ubicación y el horario | `test_formas_incompletas_de_primer_contacto_son_pregunta_informativa` |
| D46 | Una segunda pregunta sin dato daba el mismo texto, y la regla contra repeticiones (D27) lo sustituía por «Sigo atento…» o «Sigo esperando tu respuesta», sin responder | Misma prueba | La segunda vez responde «Tampoco encuentro ese dato en la investigación…» | `test_dos_preguntas_sin_dato_no_terminan_en_sigo_atento` |
| D47 | Con un intercambio ya registrado, un pago sin relación («Ya pagué la inscripción…») se toma como participación propia y cambia la pregunta pendiente a B15 | Revisión de la misma prueba | Pendiente: la participación debería exigir que el pago se vincule con el intercambio | — |
