# Artículo — Tecnología en Marcha

Artículo en LaTeX con el formato de la plantilla de **Tecnología en Marcha**
(TEC). Partió de un primer borrador de las personas autoras
([`articulo_tecnologia_en_marcha.md`](../articulo_tecnologia_en_marcha.md)) y
después se alineó con el documento de investigación y con los resultados de los
pilotos: la sección [Historia del texto](#historia-del-texto) cuenta qué cambió
y por qué.

## Compilar en la computadora (MiKTeX y TeXworks)

**Todo el artículo, con bibliografía:** doble clic en `compilar.bat`. Corre
pdfLaTeX → Biber → pdfLaTeX → pdfLaTeX y deja `tecnologia-en-marcha.pdf` en
esta carpeta. Si algo falla, muestra el error y la línea: `l.20` es la línea
20 del archivo de sección que se estaba leyendo.

Al abrirlo desde `\\wsl$\...`, la consola puede avisar que "no admite rutas
UNC". Es un aviso inofensivo: el script entra a la carpeta con `pushd`.

**Mientras se edita texto:** en TeXworks, el botón de compilar con
**pdfLaTeX** alcanza, desde cualquier archivo de `contenido/`. La primera
línea de cada uno (`% !TEX root`) le dice a TeXworks que compile el archivo
principal. Hace falta `compilar.bat` solo cuando cambian las citas o
`referencias.bib`, porque Biber no corre desde el botón.

Todos los `.tex` declaran `% !TEX encoding = UTF-8 Unicode`, para que las
tildes no se rompan aunque TeXworks tenga otra codificación por defecto.

## Compilar en Overleaf

1. Subir el contenido de esta carpeta a un proyecto nuevo (*New Project →
   Upload Project*, con un .zip de `articulo/`).
2. *Menu → Compiler*: **pdfLaTeX**. *Main document*:
   **`tecnologia-en-marcha.tex`**.
3. Compilar. Overleaf corre `biber` solo para la bibliografía.

## Estructura

| Archivo | Contenido |
|---|---|
| `tecnologia-en-marcha.tex` | Preámbulo y formato de la plantilla |
| `compilar.bat` | Compilación completa con bibliografía, en Windows |
| `contenido/00-metadatos.tex` | Título, autores, resumen, palabras clave |
| `contenido/01-…06-*.tex` | Una sección por archivo |
| `contenido/figura-arquitectura.tex` | Figura 1, dibujada en TikZ |
| `figuras/*.png` | Figuras 2 a 4, generadas con `make figuras` (D62) |
| `contenido/macros.tex` | Marcas de revisión |
| `referencias.bib` | Bibliografía verificada |

El contenido está separado del formato a propósito: si el artículo termina en
otra revista —por ejemplo **Revista Ingeniería** (UCR), cuya guía también está
disponible—, se agrega otro archivo principal y las secciones no cambian.

## Marcas de revisión

El PDF muestra dos tipos de marca:

- **[Pendiente: …]** en rojo: algo que falta escribir o decidir.
- **[Revisar: …]** en naranja: una afirmación del texto que no coincide con la
  evidencia del repositorio o que no se pudo verificar.

Antes del envío, en `contenido/macros.tex` cambiar `\notastrue` por
`\notasfalse`: las marcas desaparecen sin tocar el texto.

## Historia del texto

### La conversión del borrador

La primera versión en LaTeX conservó la redacción del borrador palabra por
palabra. Se comprobó comparando las palabras del borrador con las de los
`.tex`, sin acentos ni comandos. Cambiaron cuatro cosas:

1. **Acentos restaurados.** El .md y el .docx venían sin tildes.
2. **La referencia de CRISP-ML(Q) estaba mal.** Los autores 5 a 7 son
   Winkler, Peters y Müller, verificados en Crossref y arXiv. "Ludwig,
   Lauber-Rönsberg, Klöpper" venía de `docs/crisp-ml-q.md`, donde se escribió
   de memoria.
3. **La segunda frase de Agradecimientos** era una nota para las personas
   autoras y pasó a marca de pendiente.
4. **Bloque de autores**: los nombres de las dos personas autoras de la tesis
   y la afiliación a la Universidad CENFOTEC, donde había marcadores.

Después, las personas autoras quitaron la sección "Declaración sobre el uso
de inteligencia artificial" (ver pendiente 1).

### La alineación con la investigación (PIA02)

Una revisión contra el documento de investigación y contra los expedientes de
los pilotos encontró tres desvíos. Se corrigieron en cuatro cambios, y desde
entonces el texto ya no es solo el del borrador:

1. **Hallazgos.** Resultados reporta lo que encontró el marco —las variables
   dominantes, el desempeño como contexto, las 4 combinaciones de Aruba
   (Cuadro 3) y las 29 del multi-hogar, con el caso de Cook—, y la Discusión,
   los cuatro límites que declara el expediente. Todas las cifras salen de los
   expedientes.
2. **Diseño metodológico.** Design Science Research, enfoque mixto y tres
   fases, y una subsección nueva sobre cómo se derivaron los requerimientos
   (PIA02, capítulos 3 y 4). Las tres citas textuales de la ENIA se cotejaron
   con el PDF.
3. **Literatura.** De 7 a 21 referencias, cada una donde PIA02 la usa, todas
   verificadas.
4. **Título y figura.** El título nombra la ENIA y a las personas adultas
   mayores. La Figura 1 redibuja la arquitectura de PIA02 (Figura 2), que en
   Word está hecha con formas y no se puede extraer como imagen; pasó a
   Materiales y métodos, donde el texto la cita.

### El enfoque

El borrador abría con el caso de uso —apoyar la permanencia en el hogar y a
los cuidadores—, y eso hacía parecer que el proyecto era sobre el cuidado. El
alcance de la investigación es la batería de pruebas que verifica el
cumplimiento de la ENIA; el monitoreo de personas adultas mayores es el
dominio donde se aplica, y el proyecto con cuidadoras fue solo el antecedente
(PIA02, 1.1 y 1.7.2). El resumen y la Introducción ahora abren con la brecha
de cumplimiento, y la Introducción dice explícitamente que lo evaluado es el
marco. Se quitó además una mención a la relevancia clínica de Bed\_to\_Toilet:
la validación clínica está fuera de alcance (1.7.2).

### Las fuentes de la población

Dos marcas de revisión pedían fuente: que la residente de Aruba sea adulta
mayor y que hh107 tenga dos residentes. Las dos están en la tabla de
viviendas del depósito oficial de CASAS en Zenodo, que el artículo ya citaba
(D60). Materiales y métodos y Resultados las citan ahora, y el caso de hh107
queda como hipótesis, no como causa. La Discusión dice además de qué piloto y
de qué subgrupo sale el 0,107 de Watch\_TV.

### La estabilidad entre semillas

El profesor guía pidió medir cuánto se mueven las disparidades al cambiar la
semilla. `make estabilidad` reentrenó el modelo con diez semillas, con el plan
y la regla de lectura comprometidos en git antes de correrlo (D61). El cuarto
límite de la Discusión pasa de declarar que no se midió a reportar el
resultado, y las semillas salen del trabajo futuro de las Conclusiones.

### Los comentarios del profesor

La versión de Word que circula entre las personas autoras recibió comentarios del
profesor guía, y este LaTeX se alineó con ella: resumen y abstract, palabras
clave, un párrafo de contribuciones en la Introducción, tres figuras de
resultados, el análisis de estabilidad separado en método, resultado e
interpretación, nuevas líneas futuras, y la declaración de uso de IA. Se
incorporó además al profesor como tercer autor.

Sus propuestas se ajustaron donde no se sostenían contra los expedientes: el
"28 de 29" del resumen es solo del piloto multi-hogar (en total son 32 de 33), y
el mapa de calor codifica la TVP y no la diferencia (D62). Las contribuciones
evitan afirmar que el protocolo "no se puede alterar" o que el instrumento es
"transferible", que el estudio no demuestra.

El Word no tiene la Figura 1 de arquitectura, así que allí las figuras de
resultados son la 1, la 2 y la 3.

La revisión contra PIA01 (1.9, 4.3 y 4.4) ajustó la quinta contribución al alcance
que declara el documento: "el corpus revisado no permitió identificar", y solo para
sensores PIR en el contexto costarricense. Se agregaron tres marcos de auditoría y
evaluación (Raji et al., Z-Inspection y capAI) para ubicar el aporte frente a lo
publicado: PIA01 no los cubre. Sus descripciones salen de los resúmenes; faltan
cotejar con los artículos completos, en especial capAI, que es el más cercano.

### La revisión de fuentes y la revisión crítica

Se cotejaron las 26 referencias con Crossref y DataCite: todas existen, sus datos
coinciden y ninguna tiene avisos de retractación ni de corrección. Cambiaron tres
cosas por vigencia o por forma:

- **AI Act.** El Reglamento (UE) 2026/1744, verificado en EUR-Lex, aplazó las
  obligaciones de alto riesgo al 2 de diciembre de 2027 (anexo III) y al 2 de
  agosto de 2028 (anexo I, donde están los dispositivos médicos). La Introducción
  lo dice y la referencia lo anota.
- **Mehrabi et al.** lleva la fecha del número, julio de 2022.
- **Lundberg y Lee (2017)** queda sin páginas, como Hardt et al.; el registro de
  Zenodo, sin número de versión, porque no lo declara.

La revisión crítica agregó lo que un revisor iba a pedir: la disponibilidad del
código y de los datos, el criterio de éxito en el método, la regla de selección de
las viviendas, la etiqueta de cada ventana, la partición, los hiperparámetros, cómo
se calcula la diferencia de tasas, que los umbrales son convenciones del equipo, que
la batería incluye casos en los que la equidad aprueba y que los datos son de
Estados Unidos. El Cuadro 2 muestra los subgrupos evaluados en lugar de los nombres
de archivo, y la terminología pasó al español: ficha del modelo y ficha del
conjunto de datos.

Después se cotejó el texto con los PDF oficiales del AI Act en español y del NIST
AI 100-1. Lo que el artículo dice de ambos coincide: las obligaciones de alto
riesgo son las de los artículos 9 a 14, y los dispositivos médicos (productos
sanitarios, anexo I) solo son de alto riesgo si además pasan una evaluación de
conformidad por terceros (art. 6.1). Se adoptó el término oficial "conservación de
registros" (art. 12), los umbrales declarados antes de medir se apoyan en el
art. 9.8, que exige probar con parámetros y umbrales definidos previamente, y las
funciones del NIST quedaron en su orden: gobernar, mapear, medir y gestionar. Todo sale del repositorio (configuraciones, `src/comun/datos.py`,
`src/equidad/metricas_equidad.py`, `tests/test_equidad.py` y la sección Datos del
README).

## Pendientes para decidir

Ordenados por importancia.

1. **Tres citas por cotejar con el texto publicado.** En el Word, Trabajo
   relacionado atribuye a Batool et al. que el AI Act y el NIST son los marcos más
   citados, con transparencia y rendición de cuentas como principios principales;
   el preprint de arXiv no lo dice, y la versión publicada no se pudo leer. A Park
   et al. se les atribuyen las aplicaciones más frecuentes del dominio, que su
   resumen no menciona; sí dice que la equidad y el sesgo están poco explorados.
   Que el campo no evalúa transparencia, equidad ni gobernanza
   (Introducción, `park2025aging,habibovic2025aging`) no se pudo verificar en
   Habibovic et al., porque IEEE bloqueó el texto completo.
2. **Declaración de uso de IA.** Ya está en el texto. Falta confirmar si Laura usó
   otra herramienta y revisar la política de la revista. Los modelos de Claude salen
   de los commits del repositorio; de GitHub Copilot se nombra solo la herramienta.
3. **Dos puntos de la revisión que no entraron en los cuatro cambios:** los
   *refinamientos* que el piloto introdujo respecto de PIA02 (métricas que
   deciden, descarte de Fairlearn, piloto multi-hogar, nombres de zona), que
   el objetivo específico 3 pide documentar; y la *contribución dual
   ENIA–AI Act* para el sector healthtech, central en PIA02 y ausente en el
   artículo.
4. **Título.** Es una propuesta; la traducción al inglés también, y la
   plantilla pide evitar traductores automáticos.
5. **Figura 1.** Es un redibujo. Si se prefiere la original, exportarla desde
   Word como PNG a 300 dpi y reemplazar `contenido/figura-arquitectura.tex`.
6. **Versión de la ENIA.** La página de créditos dice *Versión 1.0, 24 de
   octubre de 2024*, con ISBN 978-9968-732-94-9; PIA02 la cita como "Versión
   2.6", que el documento no menciona. El mismo PDF se declara "versión
   simplificada" (p. 3) y remite a la completa en www.micitt.go.cr.
7. **Autores**: faltan los ORCID. Los correos y las cédulas no se versionan aquí
   porque el repositorio es público; están en la versión de Word.
8. **Palabras clave**: son las que propuso el profesor, pero la plantilla pide
   términos del tesauro de la UNESCO. Confirmar si la revista lo exige.
9. **AI Act**: la referencia usa el título en inglés. El oficial en español, cotejado
   con el PDF del DOUE, es "Reglamento (UE) 2024/1689 del Parlamento Europeo y del
   Consejo, de 13 de junio de 2024, por el que se establecen normas armonizadas en
   materia de inteligencia artificial […] (Reglamento de Inteligencia Artificial)".
   Falta decidir si la referencia pasa al español.

## Correcciones para PIA02

La revisión encontró en el documento de investigación cosas que no deberían
pasar al artículo:

- La ENIA como "Versión 2.6": es la 1.0 (ver pendiente 5).
- "La ENIA reconoce textualmente la edad como variable protegida" (1.4, 2.5,
  4.1.2, 5.4 y Tabla 5). El texto dice "respetando las diferencias de edad,
  etnia, género…", en el contexto de la accesibilidad (p. 32). "Variable
  protegida" es una interpretación, no una cita textual.
- La cita "realizar auditorías y pruebas continuas para identificar y corregir
  cualquier sesgo potencial" está en la p. 33, no en la 32 (4.1.2).
- El principio 3 se cita en "pp. 31-32"; está en la p. 32.
- Mitchell et al. (2019) como "FAccT '19": en 2019 el congreso se llamaba
  FAT\*.

Kim et al. (2022), que citan las fichas de caracterización de los
expedientes, sí existe: es una de las revisiones de alcance de PIA02, y el
artículo la cita.
