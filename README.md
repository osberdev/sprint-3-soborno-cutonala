# Orientación sobre soborno académico · CUTonalá

Chatbot de orientación para estudiantes del Centro Universitario de Tonalá (CUTonalá), UDG, ante posibles casos de soborno académico. Es el módulo individual del chatbot del equipo verde para *Metodologías del desarrollo ágil*; se desarrolló a partir del Sprint 3 (Primer Contacto).

## Tema individual

El proyecto aborda relatos de posible soborno académico: solicitudes u ofrecimientos de dinero, bienes u otros beneficios asociados con aprobar una materia u obtener una ventaja académica. El chatbot orienta en tres niveles (personal, universitario y legal) con información de la investigación `Investigacion_soborno_CUTonala.docx`, contextualizada al CUTonalá y a Primer Contacto. No verifica los hechos ni determina responsabilidades.

La entrega es individual; los temas de los demás integrantes no se han integrado.

## Cómo funciona

```text
Mensaje del estudiante
  -> autómata: reglas B1–B17 sobre la ficha del caso; decide la etapa (q0–q6, qS)
  -> búsqueda en conocimientos/ (local o FAISS), filtrada por la etapa o por la pregunta informativa
  -> respuesta local de la etapa, con el dato recuperado y sus fuentes
  -> (opcional) Gemini la redacta; si menciona un dato que no está en lo enviado, se muestra la local
  -> la pregunta de sí o no de la etapa, al final y textual
```

El autómata decide; Gemini, si se activa, solo cambia la forma de decirlo. La decisión es la misma en todos los modos.

### Estados

| Estado | Fase | Instancia |
|---|---|---|
| q0 Inicial | 1/3 Comprender | — |
| q1 Aclaración | 1/3 Comprender | — |
| q2 Personal | 2/3 Orientar en CUTonalá | Unidad de Orientación Educativa · CAE, segundo piso |
| q3 Primer Contacto | 2/3 Orientar en CUTonalá | Primer Contacto · CAE, primera puerta a la izquierda |
| q4 Académica | 2/3 Orientar en CUTonalá | Coordinación de Ingeniería en Ciencias Computacionales → jefatura del departamento responsable de la materia |
| q5 Autoridad externa | 3/3 Orientar fuera de la UdeG | Fiscalía Especializada en Combate a la Corrupción de Jalisco |
| q6 Asesoría jurídica | 3/3 Orientar fuera de la UdeG | Procuraduría Social de Jalisco |
| qS Seguridad | Interrupción | Servicios de emergencia o seguridad; intervención en crisis en el CAE |

Las transiciones están en `TRANSICIONES` (`automata_soborno.py`) y una prueba exige que coincidan con el diagrama aprobado. Las decisiones del estudiante (B10, B14, B15) y las de seguridad (B16, B17) son preguntas de sí o no; una duda se repregunta una vez y después no se insiste. Al salir de Seguridad, el caso vuelve a q1 y recorre de nuevo las flechas que ya había tomado.

Además, el autómata:

- responde «No tengo información oficial…» a una pregunta que la investigación no contesta, sin abrir un caso;
- responde una pregunta hipotética («¿y si…?») sin registrarla como hecho;
- no cuenta un pago institucional ordinario (inscripción, colegiatura…) como participación en un intercambio;
- remite a otro tema del equipo lo que no es soborno (acoso sexual, favoritismo sin beneficio, cuotas sin condicionamiento).

## Modos de ejecución y qué sale del equipo

| Comando | Qué hace | Qué se envía a un servicio externo |
|---|---|---|
| `python3 chatbot_soborno.py` | Conversación local; guarda el caso entre ejecuciones | Nada |
| `--gemini` | Gemini redacta la orientación; se verifica contra lo enviado | Tarjeta del estado con hechos en frases neutras y fragmentos de la investigación. **No el texto de los mensajes** |
| `--extractor-gemini` | Gemini detecta hechos de una lista cerrada, con cita textual | **El texto de cada mensaje** (salvo antecedentes y sí/no). Solo con relatos ficticios |
| `--faiss` | Búsqueda vectorial sobre `conocimientos/` | Consulta armada con la etapa y los hechos neutros. **No el texto de los mensajes** |
| `--reindexar-faiss` | Reconstruye el índice FAISS | Los fragmentos de la investigación |
| `--demo`, `--pregunta "…"` | Conversación de ejemplo o un solo mensaje | Nada; no escriben en disco |
| `--sin-guardar` | Desactiva el guardado del caso | — |

Las peticiones a Gemini usan `store=False`, temperatura 0.2 y una espera máxima de 20 segundos; si fallan, se muestra la respuesta local y se informa del fallo. El modelo se configura en un solo lugar, `gemini_soborno.py` (`gemini-3.5-flash-lite` por defecto o la variable `GEMINI_MODEL`). La clave se carga en la terminal (`GEMINI_API_KEY`) y no forma parte del repositorio. La seudonimización de relatos no está aprobada.

### Retomar un caso entre ejecuciones

En la conversación interactiva, el caso se guarda después de cada turno en `caso_guardado.local.json`, excluido de Git. Contiene el estado del autómata, la pregunta pendiente, el camino recorrido y la ficha (indicadores como «hubo intercambio» o «amenaza académica» y las decisiones de sí o no); nunca el texto de los mensajes. Al iniciar, el programa pregunta si se retoma: «sí» continúa con la pregunta pendiente; «no» lo borra. `olvidar` o `reset` lo borran durante la conversación. Un archivo dañado o alterado se ignora con un aviso.

## Base de conocimientos

`conocimientos/` contiene la investigación segmentada en 13 archivos Markdown, generados con `herramientas/segmentar_investigacion.py` desde el `.docx` y comprobados palabra por palabra contra él. `manifiesto.json` indica qué apartados contiene cada archivo, qué estados lo consultan, qué apartados se excluyen (portada, escenarios del capítulo 9, capítulo 12 de diseño del prototipo, conclusiones) y qué texto de diseño no se indexa (`no_indexar`).

Los textos escritos para el programa (orientación de cada estado, preguntas, respuestas informativas) usan los nombres completos de instituciones y normas tal como aparecen en la investigación. Una prueba extrae cada nombre del código y exige que exista en la investigación, y otra que cada referencia [S##] exista en `fuentes.json`.

### Relatos de clase sobre docentes identificados

Los relatos C01 y C02 de la investigación mencionan intercambios presuntos, pero no enlazan esos hechos con nombres. El ejemplo nominal planteado en clase se refería hipotéticamente a otra conducta; no se agrega como caso de soborno. La ausencia de una resolución oficial no impide registrar un testimonio directo: la respuesta debe indicar quién lo relató, qué conducta se atribuye, qué soporte hay y qué sigue sin comprobarse.

Para un testimonio que sí vincule una persona concreta con una solicitud o entrega por una ventaja académica, crea `conocimientos/casos_docentes.local.json` a partir del archivo de ejemplo. Cada entrada de `casos` requiere `id`, `persona`, `tema` (`soborno` o `evaluacion`), `conducta`, `procedencia`, `fecha_registro`, `soporte` y `estado`; `alias`, `beneficio` (`dinero`, `botella` u `otro`), `materia`, `ciclo`, `resultado` y `contexto_evaluacion` son opcionales. `procedencia` debe precisar si es experiencia directa, entrevista, comentario indirecto o documento; `estado` distingue un relato sin corroborar de una denuncia o resolución. La función de consulta lee este archivo sin reconstruir FAISS, distingue el posible intercambio del trato preferencial y presenta los señalamientos como tales. No lo envía a Gemini.

Este repositorio de GitHub es público. El archivo local con nombres está excluido de Git; su inclusión en una base compartida requiere acordar con el equipo qué datos se comparten y con quién. El registro `relatos_campus.md` y el índice FAISS contienen solamente relatos sin nombres.

## Relación con la base compartida del profesor

`app.py` y `Base.rar` muestran el flujo de referencia del equipo: cargar PDF de `conocimientos/`, dividirlos en fragmentos de 1 000 caracteres con 200 de solapamiento, producir embeddings con `gemini-embedding-2`, guardar un índice FAISS y recuperarlo en consultas posteriores. El índice entregado en `Base.rar` corresponde a otros documentos universitarios; no se mezcla con la base del módulo de soborno. Su archivo `index.pkl` no se carga, porque la deserialización de un archivo recibido puede ejecutar contenido no confiable.

Este módulo conserva el contrato sencillo `buscar(pregunta, estado, limite=3)` para que el chat use el buscador local o FAISS. También conserva el autómata, las rutas de orientación y los identificadores de fuentes existentes. **Los archivos `faiss_index_soborno/` no son compatibles directamente con `FAISS.load_local()` de `app.py`:** aquí el índice se guarda con FAISS y los metadatos en JSON, sin `index.pkl`. Para integrar con el equipo hay dos rutas concretas: llevar los archivos de `conocimientos/` (excepto `relatos_campus.md` y el manifiesto) a la carpeta `conocimientos/` de la aplicación compartida, en el formato que su cargador lea, y reconstruir su índice LangChain, o conectar `BuscadorFaiss` como buscador del módulo individual. En la primera ruta, `app.py` carga automáticamente el índice viejo si encuentra `faiss_index/`; hay que conservarlo como respaldo fuera de esa ruta antes de ejecutar la reconstrucción. Antes de mezclar documentos, el equipo debe revisar procedencia y duplicados; los relatos indirectos no se convierten en hechos sobre docentes identificados.

### Construir y consultar FAISS

Desde la iteración 6 (13 de noviembre de 2026), el índice se construye con los mismos fragmentos que usa la búsqueda local: los archivos de orientación de `conocimientos/` con las exclusiones del manifiesto (capítulo 12, apartado 8.2 y frases de diseño del prototipo), divididos en partes de 1 000 caracteres con 200 de solapamiento, y el registro `relatos_campus.md` como grupo aparte. Cada vector conserva en JSON su apartado, archivo, fuentes y estados del autómata.

| Aspecto | `app.py` del equipo | Este módulo |
|---|---|---|
| Fuente | PDF de `conocimientos/` | Archivos Markdown de `conocimientos/` según `manifiesto.json` |
| Fragmentos | 1 000 / 200 caracteres | 1 000 / 200 caracteres, sin cruzar apartados |
| Metadatos | `index.pkl` (pickle) | JSON, sin deserialización con pickle |
| Consulta | El texto de la pregunta | Etapa, reglas, pregunta informativa y hechos del caso en frases neutras; nunca el mensaje del estudiante |
| Filtro | Ninguno (`k=4`) | El mismo que la búsqueda local: archivos de la pregunta informativa o del estado del caso |

```bash
python -m pip install -r requirements-faiss.txt
read -rs 'GEMINI_API_KEY?Pega la clave y pulsa Enter: '
export GEMINI_API_KEY
python chatbot_soborno.py --reindexar-faiss
python chatbot_soborno.py --faiss
```

La indexación requiere clave y conexión a Gemini para generar los embeddings (97 fragmentos de orientación y 8 de relatos con la base actual). Si cambia un archivo de `conocimientos/` o el manifiesto, el programa pide reconstruir el índice. El índice queda fuera de Git. Si la consulta vectorial falla durante una conversación, se usa la búsqueda local y se informa del fallo. Se puede combinar `--faiss --gemini`.

La reconstrucción conserva por separado cada grupo ya indexado. Si Gemini devuelve un límite temporal (429), espera el reintento automático; si la ejecución termina sin completar ambos grupos, vuelve a lanzar `--reindexar-faiss` cuando se restablezca la cuota.

## Archivos

| Archivo | Función |
|---|---|
| `chatbot_soborno.py` | Entrada del chat, búsqueda local, filtro por etapa o pregunta, caso guardado. |
| `automata_soborno.py` | Autómata aprobado: estados, reglas B1–B17, ficha del caso, preguntas de sí o no, textos de orientación. |
| `gemini_soborno.py` | Gemini: configuración única, redacción verificada contra el contexto, extractor de hechos con citas. |
| `faiss_soborno.py` | Índice FAISS sobre `conocimientos/` con metadatos JSON. |
| `sprint3_soborno.py` | Respuestas a las preguntas informativas sobre Primer Contacto (Sprint 3) y demostración del autómata por consola. |
| `casos_consulta.py` | Consulta de antecedentes con procedencia y estado del relato. |
| `conocimientos/` | Investigación segmentada, manifiesto, registro de relatos y ejemplo de registro nominal. |
| `herramientas/segmentar_investigacion.py` | Regenera `conocimientos/` desde el `.docx` (`--verificar` solo comprueba). |
| `herramientas/correr_pruebas.py` | Ejecuta todas las suites y resume el resultado. |
| `fuentes.json` | Identificadores de fuente y enlaces. |
| `Investigacion_soborno_CUTonala.docx` | Investigación formal. |
| `docs/registro_defectos.md` | Registro de defectos D01–D56, defectos del diagrama G01–G06, riesgos y seguimiento por iteración. |
| `evidencias/` | Ejecuciones de pruebas, conversaciones y resumen de las pruebas manuales. |

## Pruebas

Con Python 3.10 o posterior, desde esta carpeta:

```bash
python3 herramientas/correr_pruebas.py
```

| Suite | Pruebas | Qué comprueba |
|---|---|---|
| `pruebas_automata.py` | 50 | Tabla de transiciones contra el diagrama, casos límite, regresiones de las pruebas manuales, nombres exactos |
| `escenarios_aceptacion.py` | 1 (21 escenarios) | Escenarios de aceptación aprobados: 9.x de la investigación y guion de prueba manual |
| `pruebas_conocimientos.py` | 14 | Fidelidad textual con el `.docx`, exclusiones, recuperación por etapa, extractos sin repetición |
| `pruebas_chatbot.py` | 8 | Chat en modo local |
| `pruebas_gemini.py` | 24 | Qué se envía a Gemini, siete datos inventados que regresan a la respuesta local, eco de instrucciones, extractor con citas, fallos |
| `pruebas_persistencia.py` | 7 | Retomar un caso da el mismo resultado; el archivo no contiene mensajes; datos alterados se rechazan |
| `pruebas_faiss_y_casos.py` | 14 | Registro de relatos; FAISS real con embeddings ficticios (se omiten 5 sin `faiss-cpu`) |

Ninguna prueba llama a servicios externos. `python3 chatbot_soborno.py --demo` reproduce una conversación de ejemplo.

## Evidencias

- `evidencias/pruebas_locales_2026-11-13.txt`: las 118 pruebas, en un Python sin dependencias opcionales y en otro con `google-genai`, `faiss-cpu` y `numpy`.
- `evidencias/conversacion_local_2026-11-13.txt`: conversación reproducible que recorre B1, pregunta sin dato, q2, q6, antecedentes, Seguridad y retorno, hipótesis, causa benéfica e insinuación.
- `evidencias/pruebas_manuales_2026-11-12_13.md`: resumen de las sesiones manuales del autor en modo local, Gemini y FAISS, y los defectos que encontró cada una.
- `evidencias/*_2026-10-13.txt`, `consulta_gemini_01.txt` y `entorno_gemini.txt`: versión anterior al autómata actual (13 de octubre de 2026); se conservan como historial.

Estos resultados comprueban el comportamiento del programa en casos concretos; no certifican la precisión jurídica del contenido ni el reconocimiento de cualquier redacción.

## Documentación de los tres niveles

Los tres niveles están contenidos en la investigación Word y en su versión de texto:

| Nivel solicitado | Apartados de la investigación | Contenido documentado |
|---|---|---|
| Personal | Capítulo 4 | Primeras decisiones, registro de información, bienestar y continuidad escolar. |
| UDG | Capítulos 5 y 6 | Funciones institucionales, orientación, recursos y directorio de responsables. |
| Legal | Capítulo 7 | Fundamentos examinados, valoración externa, presentación de información y seguimiento. |

Se adjunta la investigación existente; esta preparación de evidencias no constituye una nueva verificación de sus contactos, plazos o fuentes. El capítulo 8 relaciona los niveles y el capítulo 12 describe su aplicación al prototipo.

## Límites de la versión

- El reconocimiento depende de reglas y vocabulario; el extractor de Gemini amplía la cobertura, pero solo con relatos ficticios mientras la seudonimización no esté aprobada.
- Una pregunta en presente («¿qué hago si me pide dinero?») se trata como relato, no como hipótesis.
- La verificación de la redacción de Gemini comprueba datos concretos (correos, enlaces, cifras, plazos e instancias); no el sentido de cada afirmación.
- La calidad del orden en FAISS depende de la consulta armada con la etapa; los apartados prioritarios de cada etapa se fijan igual que en el modo local.
- No tiene interfaz gráfica, folio ni envío de denuncias. El caso guardado es local y de una sola persona; no es un expediente.

Repositorio: https://github.com/osberdev/orientacion-soborno-academico-cutonala (público; antes `sprint-3-soborno-cutonala`).
