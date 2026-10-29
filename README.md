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
| `chatbot_soborno.py` | Entrada del chat, búsqueda documental y conexión opcional con Gemini. |
| `sprint3_soborno.py` | Reglas, estado y memoria de la sesión. |
| `conocimientos/investigacion_soborno.md` | Texto de la investigación utilizado como base documental. |
| `conocimientos/primer_contacto_soborno.md` | Ficha institucional que consulta el motor de reglas. |
| `conocimientos/casos_soborno.md` | Relatos anónimos no corroborados, con procedencia, datos faltantes y límites de uso. |
| `conocimientos_pdf/` | Dos PDF independientes: investigación de procesos y registro de relatos. |
| `faiss_soborno.py` | Construcción y consulta opcional del índice FAISS individual desde esos PDF. |
| `casos_consulta.py` | Respuesta prudente a preguntas por antecedentes de docentes. |
| `fuentes.json` | Relación entre identificadores de fuente y enlaces. |
| `Investigacion_soborno_CUTonala.docx` | Investigación formal para lectura y entrega. |
| `pruebas_chatbot.py` | Siete pruebas automatizadas; incluyen un cliente simulado de Gemini. |
| `pruebas_faiss_y_casos.py` | Ocho pruebas locales del registro, la transición a un relato directo, la extracción de PDF, la presentación de resultados, el respaldo cuando falla la búsqueda vectorial y la reanudación del índice. |
| `evidencias/` | Salidas obtenidas al ejecutar pruebas y consultas el 13 de octubre de 2026. |

El modo predeterminado conserva la recuperación por términos y prioridades documentales. Existe además un modo FAISS opcional basado en los dos PDF individuales. La memoria conserva información durante la sesión y se reinicia con `reset`. Una pregunta general por antecedentes consulta el registro sin incorporarse como hecho del caso personal.

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

Hasta que se ejecute `--reindexar-faiss` con una clave válida, el índice individual no existe y el modo `--faiss` no está verificado en una llamada real a la API. El modo local sigue funcionando sin esa dependencia. Si falla la consulta vectorial durante una conversación, se utiliza la búsqueda local y se informa del fallo.

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
python3 pruebas_faiss_y_casos.py
python3 chatbot_soborno.py --demo
python3 chatbot_soborno.py
```

La primera instrucción ejecuta las pruebas automatizadas; la segunda reproduce consultas ficticias; la tercera abre una conversación. Usa `reset` para otro caso y `salir` para cerrar.

## Evidencias disponibles

- `evidencias/pruebas_locales_2026-10-13.txt`: siete pruebas ejecutadas y aprobadas. Comprueban recuperación del directorio, selección documental, tratamiento de comentarios indirectos, memoria ante represalia académica, diferenciación de amenaza física, referencias y preparación de la solicitud a Gemini mediante un cliente simulado.
- `evidencias/consultas_locales_2026-10-13.txt`: interacción ejecutada con consulta institucional, comentario indirecto, reinicio y un relato directo seguido de una posible represalia académica. Incluye respuestas, estados y fragmentos recuperados.
- `evidencias/consulta_gemini_01.txt`: consulta real ejecutada por el usuario el 13 de octubre de 2026 desde Ubuntu, sobre una solicitud de dinero para aprobar. La salida muestra `Gemini + autómata + documentos`, estado `{'x': 4, 'y': 3}`, prioridad `prioritaria` y recuperación de los apartados 5.1, 7.3 y 4.2. Se verificó que el archivo contiene la respuesta y las referencias. Esta consulta aislada no prueba la continuidad de una conversación con Gemini.

Estos resultados comprueban comportamientos de software en casos concretos; no certifican la precisión jurídica del contenido ni el reconocimiento de cualquier redacción posible.

## Gemini y pendientes de esta entrega

Existe una integración opcional con Gemini. El 13 de octubre de 2026 se registró una consulta real satisfactoria en `evidencias/consulta_gemini_01.txt`. La respuesta identifica las tres vías de orientación, evita determinar responsabilidad y solicita información adicional. Esta revisión confirma el funcionamiento observado; no constituye una validación jurídica independiente de la respuesta. En pruebas anteriores también se observó un fallo del servicio con respuesta local de respaldo.

Para usar la integración se necesita la dependencia `google-genai` y una clave en la variable de entorno `GEMINI_API_KEY`. La clave se carga únicamente en la terminal del usuario y no forma parte del repositorio.

Entorno registrado para la prueba: `google-genai 2.29.0`, según `evidencias/entorno_gemini.txt`. La variable `GEMINI_MODEL` no estaba definida; el código de `chatbot_soborno.py` configura por defecto `gemini-3.5-flash-lite`. Este nombre identifica el modelo solicitado por el programa; la salida guardada no incluye metadatos del modelo devueltos por el servicio.

Repositorio de GitHub: https://github.com/osberdev/sprint-3-soborno-cutonala. Su visibilidad se comprobó como pública el 29 de octubre de 2026.

## Límites de la versión

- El reconocimiento depende de reglas y coincidencias de palabras; necesita pruebas adicionales con otras redacciones.
- No tiene interfaz gráfica, expediente persistente, folio ni envío de denuncias.
- Los enlaces se recuperan del índice local; no verifican automáticamente todas las afirmaciones de una respuesta de Gemini.
- Para las pruebas se utilizan relatos ficticios sin identificar personas reales.
