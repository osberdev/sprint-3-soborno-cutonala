# Sprint 3 personal — Soborno académico en CUTonalá

## Tema individual

El proyecto aborda relatos de posible soborno académico: solicitudes u ofrecimientos de dinero, bienes u otros beneficios asociados con aprobar una materia u obtener una ventaja académica. El prototipo permite describir un caso ficticio o consultar la documentación reunida para orientar al estudiante. Distingue comentarios indirectos de relatos directos y contempla la continuidad de la conversación.

La investigación individual se organiza en los niveles personal, universitario y legal. El prototipo ofrece información preliminar con referencias; no verifica los hechos ni determina responsabilidades.

## Alcance del avance que se entrega

La entrega reúne código individual, documentación de los tres niveles y resultados reproducibles de consultas y pruebas locales. No se han integrado los temas de otros compañeros.

Este repositorio se inicia con el trabajo ya existente. Su primer commit documenta la versión recopilada el 13 de octubre de 2026; no representa un historial de desarrollo de los días anteriores.

## Estructura y funcionamiento

```text
Mensaje del estudiante
  -> reglas y estado del autómata
  -> recuperación de apartados de la investigación
  -> respuesta local o redacción con Gemini
  -> fragmentos recuperados y enlaces de sus fuentes
```

| Archivo | Función |
|---|---|
| `chatbot_soborno.py` | Entrada del chat y búsqueda documental. |
| `gemini_soborno.py` | Conexión opcional con Gemini: configuración única del modelo, redacción verificada contra el contexto y extractor de hechos con citas. |
| `automata_soborno.py` | Autómata aprobado: estados q0–q6 y qS, reglas B1–B17, registro del caso y preguntas de sí o no. |
| `sprint3_soborno.py` | Respuestas a las seis preguntas de Primer Contacto del Sprint 3 y demostración del autómata por consola. |
| `conocimientos/*.md` (13 archivos) | La investigación segmentada por tema, transcrita sin cambios desde el `.docx`. |
| `conocimientos/manifiesto.json` | Qué apartados contiene cada archivo, qué estados del autómata lo consultan y qué apartados se excluyen. |
| `herramientas/segmentar_investigacion.py` | Regenera los archivos de conocimiento desde el `.docx` (`--verificar` solo comprueba). |
| `conocimientos/primer_contacto_soborno.md` | Ficha institucional de una versión anterior; ningún módulo la consulta. |
| `conocimientos/relatos_campus.md` | Relatos aportados sin nombres, con procedencia, datos faltantes y límites de uso, más el apartado 10.4 de la investigación. |
| `conocimientos/casos_docentes.ejemplo.json` | Estructura vacía para registrar testimonios nominales por separado. |
| `conocimientos_pdf/` | Dos PDF independientes: investigación de procesos y registro de relatos. |
| `faiss_soborno.py` | Construcción y consulta opcional del índice FAISS individual desde esos PDF. |
| `casos_consulta.py` | Consulta de antecedentes con procedencia y estado del relato. |
| `fuentes.json` | Relación entre identificadores de fuente y enlaces. |
| `Investigacion_soborno_CUTonala.docx` | Investigación formal para lectura y entrega. |
| `pruebas_chatbot.py` | Pruebas de integración del chat en modo local. |
| `pruebas_persistencia.py` | Pruebas de la reanudación de un caso entre ejecuciones: mismo resultado que sin interrupción, sin texto de los mensajes en el archivo, datos inválidos rechazados. |
| `pruebas_gemini.py` | Pruebas de la integración con Gemini mediante un servicio simulado: qué se envía, datos inventados, extractor y fallos. |
| `pruebas_conocimientos.py` | Comprueba que los archivos de conocimiento coinciden textualmente con la investigación y que nada excluido llega al estudiante. |
| `escenarios_aceptacion.py` | Criterios de aceptación del autómata nuevo (escenarios 9.1–9.10 y guion de prueba manual). |
| `pruebas_automata.py` | Comprueba que la tabla de transiciones coincide con el diagrama aprobado y cubre casos límite. |
| `pruebas_faiss_y_casos.py` | Nueve pruebas locales del registro, la transición a un relato directo, la extracción de PDF, la presentación de resultados, el respaldo cuando falla la búsqueda vectorial y la reanudación del índice. |
| `evidencias/` | Salidas obtenidas al ejecutar pruebas y consultas el 13 de octubre de 2026. |

### Retomar un caso entre ejecuciones

En la conversación interactiva, el caso se guarda después de cada turno en `caso_guardado.local.json`, excluido de Git. El archivo contiene solo el estado del autómata, la pregunta pendiente, el camino recorrido y la ficha (indicadores como «hubo intercambio» o «amenaza académica» y las decisiones de sí o no); nunca el texto de los mensajes ni las respuestas. Al iniciar, si existe un caso guardado, el programa pregunta si se retoma: «sí» continúa donde se quedó, con la pregunta pendiente; «no» lo borra. Durante la conversación, `olvidar` o `reset` borran el archivo. `--sin-guardar` desactiva el guardado; `--demo` y `--pregunta` nunca escriben en disco. Un archivo dañado o alterado (estado, flecha o valor fuera del autómata) se ignora con un aviso.

El modo predeterminado conserva la recuperación por términos y prioridades documentales. Existe además un modo FAISS opcional basado en los dos PDF individuales. La memoria conserva información durante la sesión y se reinicia con `reset`. Una pregunta general por antecedentes consulta el registro sin incorporarse como hecho del caso personal.

### Relatos de clase sobre docentes identificados

Los relatos C01 y C02 de la investigación mencionan intercambios presuntos, pero no enlazan esos hechos con nombres. El ejemplo nominal planteado en clase se refería hipotéticamente a otra conducta; no se agrega como caso de soborno. La ausencia de una resolución oficial no impide registrar un testimonio directo: la respuesta debe indicar quién lo relató, qué conducta se atribuye, qué soporte hay y qué sigue sin comprobarse.

Para un testimonio que sí vincule una persona concreta con una solicitud o entrega por una ventaja académica, crea `conocimientos/casos_docentes.local.json` a partir del archivo de ejemplo. Cada entrada de `casos` requiere `id`, `persona`, `tema` (`soborno` o `evaluacion`), `conducta`, `procedencia`, `fecha_registro`, `soporte` y `estado`; `alias`, `beneficio` (`dinero`, `botella` u `otro`), `materia`, `ciclo`, `resultado` y `contexto_evaluacion` son opcionales. `procedencia` debe precisar si es experiencia directa, entrevista, comentario indirecto o documento; `estado` distingue un relato sin corroborar de una denuncia o resolución. La función de consulta lee este archivo sin reconstruir FAISS, distingue el posible intercambio del trato preferencial y presenta los señalamientos como tales. No lo envía a Gemini.

Este repositorio de GitHub es público. El archivo local con nombres está excluido de Git; su inclusión en una base compartida requiere acordar con el equipo qué datos se comparten y con quién. El PDF y el índice FAISS actuales contienen solamente los relatos sin nombres.

## Relación con la base compartida del profesor

`app.py` y `Base.rar` muestran el flujo de referencia del equipo: cargar PDF de `conocimientos/`, dividirlos en fragmentos de 1 000 caracteres con 200 de solapamiento, producir embeddings con `gemini-embedding-2`, guardar un índice FAISS y recuperarlo en consultas posteriores. El índice entregado en `Base.rar` corresponde a otros documentos universitarios; no se mezcla con los PDF del módulo de soborno. Su archivo `index.pkl` no se carga, porque la deserialización de un archivo recibido puede ejecutar contenido no confiable.

Este módulo conserva el contrato sencillo `buscar(pregunta, estado, limite=3)` para que el chat use el buscador local o FAISS. También conserva el autómata, las rutas de orientación y los identificadores de fuentes existentes. **Los archivos `faiss_index_soborno/` no son compatibles directamente con `FAISS.load_local()` de `app.py`:** aquí el índice se guarda con FAISS y los metadatos en JSON, sin `index.pkl`. Para integrar con el equipo hay dos rutas concretas: copiar los PDF revisados a `conocimientos/` de la aplicación compartida y reconstruir su índice LangChain, o conectar `BuscadorFaiss` como buscador del módulo individual. En la primera ruta, `app.py` carga automáticamente el índice viejo si encuentra `faiss_index/`; hay que conservarlo como respaldo fuera de esa ruta antes de ejecutar la reconstrucción. Antes de mezclar documentos, el equipo debe revisar procedencia y duplicados; los relatos indirectos no se convierten en hechos sobre docentes identificados.

### Construir y consultar FAISS

Desde Ubuntu, dentro de este repositorio y con el entorno virtual activado:

```bash
python -m pip install -r requirements-faiss.txt
read -rs 'GEMINI_API_KEY?Pega la clave y pulsa Enter: '
export GEMINI_API_KEY
python chatbot_soborno.py --reindexar-faiss
python chatbot_soborno.py --faiss
```

La indexación requiere una clave y conexión a Gemini, pues genera embeddings de los fragmentos de ambos PDF. Después guarda archivos `.faiss`, metadatos JSON y un manifiesto con huellas de los PDF en `faiss_index_soborno/`. Una consulta en modo `--faiss` también necesita la clave para convertir la pregunta en vector. Si cambian los PDF, reconstruye el índice. El índice generado queda fuera de Git; los PDF y el código sí son reproducibles. Se puede combinar `--faiss --gemini` para redactar con Gemini, o usar sólo `--faiss` para mantener la redacción local.

El modo `--faiss` ya se verificó en Ubuntu con una llamada real a la API y un índice de 107 fragmentos de procesos y 7 de relatos. El índice se conserva sólo en el entorno local de quien lo generó; cada clon debe construirlo con su propia clave. Si falla la consulta vectorial durante una conversación, se utiliza la búsqueda local y se informa del fallo.

La reconstrucción conserva por separado cada PDF ya indexado. Si Gemini devuelve un límite temporal (429), espera el reintento automático; si la ejecución termina sin completar ambos documentos, vuelve a lanzar `--reindexar-faiss` cuando se restablezca la cuota. Los grupos guardados y validados se reutilizan sin volver a generar sus vectores.

En la salida de `--faiss`, «MODO» identifica expresamente FAISS. La cabecera repetida del PDF se omite al mostrar fragmentos; los vectores almacenados no se alteran, así que este ajuste no exige reconstruir el índice. En preguntas informativas, los enlaces corresponden al apartado institucional y a los fragmentos de la misma página que el resultado principal.

## Documentación de los tres niveles

Los tres niveles están contenidos en la investigación Word y en su versión de texto:

| Nivel solicitado | Apartados de la investigación | Contenido documentado |
|---|---|---|
| Personal | Capítulo 4 | Primeras decisiones, registro de información, bienestar y continuidad escolar. |
| UDG | Capítulos 5 y 6 | Funciones institucionales, orientación, recursos y directorio de responsables. |
| Legal | Capítulo 7 | Fundamentos examinados, valoración externa, presentación de información y seguimiento. |

Se adjunta la investigación existente; esta preparación de evidencias no constituye una nueva verificación de sus contactos, plazos o fuentes. El capítulo 8 relaciona los niveles y el capítulo 12 describe su aplicación al prototipo.

## Cómo reproducir las pruebas locales

Con Python 3.10 o posterior, desde esta carpeta:

```bash
python3 pruebas_chatbot.py
python3 pruebas_gemini.py
python3 pruebas_persistencia.py
python3 pruebas_faiss_y_casos.py
python3 pruebas_conocimientos.py
python3 pruebas_automata.py
python3 escenarios_aceptacion.py
python3 chatbot_soborno.py --demo
python3 chatbot_soborno.py
```

La primera instrucción ejecuta las pruebas automatizadas; la segunda reproduce consultas ficticias; la tercera abre una conversación. Usa `reset` para otro caso y `salir` para cerrar.

## Evidencias disponibles

- `evidencias/pruebas_locales_2026-10-13.txt`: siete pruebas ejecutadas y aprobadas. Comprueban recuperación del directorio, selección documental, tratamiento de comentarios indirectos, memoria ante represalia académica, diferenciación de amenaza física, referencias y preparación de la solicitud a Gemini mediante un cliente simulado.
- `evidencias/consultas_locales_2026-10-13.txt`: interacción ejecutada con consulta institucional, comentario indirecto, reinicio y un relato directo seguido de una posible represalia académica. Incluye respuestas, estados y fragmentos recuperados.
- `evidencias/consulta_gemini_01.txt`: consulta real ejecutada por el usuario el 13 de octubre de 2026 desde Ubuntu, sobre una solicitud de dinero para aprobar. La salida, anterior al autómata actual, muestra `Gemini + autómata + documentos`, estado `{'x': 4, 'y': 3}`, prioridad `prioritaria` y recuperación de los apartados 5.1, 7.3 y 4.2. Se verificó que el archivo contiene la respuesta y las referencias. Esta consulta aislada no prueba la continuidad de una conversación con Gemini.

Estos resultados comprueban comportamientos de software en casos concretos; no certifican la precisión jurídica del contenido ni el reconocimiento de cualquier redacción posible.

## Gemini y pendientes de esta entrega

Existe una integración opcional con Gemini. El 13 de octubre de 2026 se registró una consulta real satisfactoria en `evidencias/consulta_gemini_01.txt`. La respuesta identifica las tres vías de orientación, evita determinar responsabilidad y solicita información adicional. Esta revisión confirma el funcionamiento observado; no constituye una validación jurídica independiente de la respuesta. En pruebas anteriores también se observó un fallo del servicio con respuesta local de respaldo.

Para usar la integración se necesita `google-genai` 3.3 o posterior (`requirements-gemini.txt`) y una clave en la variable de entorno `GEMINI_API_KEY`. La clave se carga únicamente en la terminal del usuario y no forma parte del repositorio.

Desde la iteración 4 (13 de noviembre de 2026) Gemini participa de dos formas independientes:

| Opción | Qué envía | Qué hace | Si falla o inventa |
|---|---|---|---|
| `--gemini` | Una tarjeta del estado (etapa, instancia, hechos del caso en frases neutras, orientación local) y los fragmentos recuperados. **No envía el texto de los mensajes ni el historial.** | Redacta la orientación. El autómata ya decidió la etapa; la pregunta de sí o no se añade después, textual. | Si la redacción contiene un correo, enlace, cifra, plazo o instancia que no está en lo enviado, se muestra la respuesta local y se indica «REDACCIÓN DE GEMINI NO FUNDAMENTADA». |
| `--extractor-gemini` | El texto de cada mensaje, salvo consultas de antecedentes y respuestas de sí o no. | Señala hechos de una lista cerrada, cada uno con una cita textual del mensaje. Solo se suman a los de las reglas locales; nunca los quitan. | Un hecho sin cita comprobable se descarta. Si el servicio falla, el turno se evalúa con las reglas locales. |

La seudonimización no está aprobada; por eso `--extractor-gemini` se usa solo con relatos ficticios. Ambas peticiones usan `store=False`, temperatura 0.2 y una espera máxima de 12 segundos. El modelo se configura en un solo lugar, `gemini_soborno.py` (`gemini-3.5-flash-lite` por defecto, o la variable `GEMINI_MODEL`).

Entorno registrado para la prueba del 13 de octubre: `google-genai 2.29.0`, según `evidencias/entorno_gemini.txt`. Esa versión es anterior a la integración actual.

Repositorio de GitHub: https://github.com/osberdev/sprint-3-soborno-cutonala. Su visibilidad se comprobó como pública el 29 de octubre de 2026.

## Límites de la versión

- El reconocimiento depende de reglas y coincidencias de palabras; necesita pruebas adicionales con otras redacciones.
- No tiene interfaz gráfica, folio ni envío de denuncias. El caso guardado es local y de una sola persona; no es un expediente.
- La verificación de la redacción de Gemini comprueba datos concretos (correos, enlaces, cifras, plazos e instancias); no comprueba el sentido de cada afirmación.
- Para las pruebas se utilizan relatos ficticios sin identificar personas reales.
