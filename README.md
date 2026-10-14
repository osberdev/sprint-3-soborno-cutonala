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
| `fuentes.json` | Relación entre identificadores de fuente y enlaces. |
| `Investigacion_soborno_CUTonala.docx` | Investigación formal para lectura y entrega. |
| `pruebas_chatbot.py` | Siete pruebas automatizadas; incluyen un cliente simulado de Gemini. |
| `evidencias/` | Salidas obtenidas al ejecutar pruebas y consultas el 13 de octubre de 2026. |

La recuperación se realiza por términos y prioridades documentales. Esta versión no utiliza embeddings ni FAISS. La memoria conserva información durante la sesión y se reinicia con `reset`.

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
python3 chatbot_soborno.py --demo
python3 chatbot_soborno.py
```

La primera instrucción ejecuta las pruebas automatizadas; la segunda reproduce consultas ficticias; la tercera abre una conversación. Usa `reset` para otro caso y `salir` para cerrar.

## Evidencias disponibles

- `evidencias/pruebas_locales_2026-10-13.txt`: siete pruebas ejecutadas y aprobadas. Comprueban recuperación del directorio, selección documental, tratamiento de comentarios indirectos, memoria ante represalia académica, diferenciación de amenaza física, referencias y preparación de la solicitud a Gemini mediante un cliente simulado.
- `evidencias/consultas_locales_2026-10-13.txt`: interacción ejecutada con consulta institucional, comentario indirecto, reinicio y un relato directo seguido de una posible represalia académica. Incluye respuestas, estados y fragmentos recuperados.

Estos resultados comprueban comportamientos de software en casos concretos; no certifican la precisión jurídica del contenido ni el reconocimiento de cualquier redacción posible.

## Gemini y pendientes de esta entrega

Existe una integración opcional con Gemini y en la sesión anterior se observaron respuestas reales y un fallo de servicio. Las evidencias nuevas incluidas aquí son locales. Falta registrar una consulta actual a Gemini con su modo de ejecución visible y revisar la respuesta.

Para usar la integración se necesita la dependencia `google-genai` y una clave en la variable de entorno `GEMINI_API_KEY`. La clave se carga únicamente en la terminal del usuario y no forma parte del repositorio. La versión instalada del SDK y el modelo deben quedar registrados al realizar la prueba real.

Repositorio de GitHub: https://github.com/osberdev/sprint-3-soborno-cutonala. Se configuró como privado; para que el profesor pueda revisarlo será necesario darle acceso con su cuenta de GitHub o acordar otro mecanismo de entrega. La visibilidad privada impide que el enlace por sí solo conceda acceso.

## Límites de la versión

- El reconocimiento depende de reglas y coincidencias de palabras; necesita pruebas adicionales con otras redacciones.
- No tiene interfaz gráfica, expediente persistente, folio ni envío de denuncias.
- Los enlaces se recuperan del índice local; no verifican automáticamente todas las afirmaciones de una respuesta de Gemini.
- Para las pruebas se utilizan relatos ficticios sin identificar personas reales.
