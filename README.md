# Registro seguro de usuarios

Aplicación escolar para practicar **Desarrollo de software seguro**. Permite registrar nombre, correo y edad, y consultar los registros en páginas de 10 usuarios. Usa Python, Flask, SQLite y HTML/CSS; no requiere instalar un servidor de base de datos ni herramientas de JavaScript.

El listado es público y no hay inicio de sesión: utiliza **datos ficticios**, como `ana@example.com`. Registrar un correo no demuestra que exista ni que pertenezca a quien lo escribió. El proyecto ilustra controles concretos; no es un sistema completo de cuentas de usuario.

## 1. Ejecutar localmente

Necesitas Python 3.11 o posterior y acceso a Internet para instalar las dependencias la primera vez. Extrae el ZIP y abre una terminal **dentro de la carpeta `software-seguro`**, donde están `app.py` y `requirements.txt`.

### Windows: PowerShell

```powershell
py -3 --version
py -3 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
Copy-Item .env.example .env
.\.venv\Scripts\python.exe app.py
```

No es necesario activar el entorno virtual ni cambiar las políticas de PowerShell. Si Windows no reconoce `py`, prueba `python` en las primeras dos líneas, después de instalar Python y habilitar su acceso desde la terminal.

### macOS o Linux

```bash
python3 --version
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
cp .env.example .env
.venv/bin/python app.py
```

Abre **[http://127.0.0.1:5000](http://127.0.0.1:5000)**. Detén el servidor con `Ctrl+C`. La base de datos y su tabla se crean automáticamente al iniciar; los registros locales quedan en `instance/users.sqlite3` y se conservan al reiniciar.

`python app.py` escucha solamente en tu equipo y mantiene el depurador desactivado. Es el servidor de desarrollo para la actividad local; la configuración pública utiliza Gunicorn en Linux.

### Configuración opcional

La aplicación lee `.env` mediante `python-dotenv`; las variables del entorno tienen prioridad. `.env.example` es una plantilla sin secretos reales y `.env` está excluido de Git.

| Variable | Uso |
| --- | --- |
| `APP_ENV` | `development` para la práctica local; `production` para el hospedaje público. |
| `SECRET_KEY` | Clave aleatoria para firmar la sesión y proteger los tokens CSRF. En producción es obligatoria y debe tener al menos 32 caracteres. |
| `DATABASE_PATH` | Ruta del archivo SQLite; el valor predeterminado corresponde a `instance/users.sqlite3` dentro del proyecto. |
| `PORT` | Puerto del servidor local; por defecto `5000`. Render proporciona su propio puerto al comando de Gunicorn. |

Para conservar las sesiones entre reinicios locales, genera una clave y copia el resultado en `SECRET_KEY=` dentro de `.env`:

```powershell
.\.venv\Scripts\python.exe -c "import secrets; print(secrets.token_urlsafe(48))"
```

En macOS/Linux, reemplaza el ejecutable por `.venv/bin/python`. No publiques la clave. Sin una clave configurada, el modo local genera una diferente en cada arranque: después de reiniciar, recarga cualquier formulario que hubieras dejado abierto para obtener un token nuevo.

## 2. Arquitectura

```text
Navegador (formulario HTML)
        |
        | POST /users + token CSRF
        v
app.py: límite de tamaño, estructura y protección CSRF
        |
        v
validation.py: normalizar -> validar -> datos aceptados
        |
        v
db.py: consulta SQL con parámetros -> SQLite
        |
        v
Redirección a GET / -> Jinja con escape HTML -> listado
```

| Archivo o carpeta | Responsabilidad |
| --- | --- |
| `app.py` | Configuración, creación de la app, rutas, cabeceras y respuestas de error. |
| `validation.py` | Reglas de normalización y validación reutilizables. |
| `db.py` | Conexiones, inicialización y consultas de la base de datos. |
| `schema.sql` | Definición de la tabla y restricciones de integridad. |
| `templates/` | Plantillas de la página y los errores. |
| `static/` | Hoja de estilos; no se necesitan recursos externos. |
| `tests/` | Pruebas automatizadas con bases temporales. |
| `requirements.txt` | Dependencias de Python. |
| `.env.example` | Ejemplo de configuración local. |
| `.gitignore` | Excluye secretos, bases locales y archivos generados. |
| `.python-version` | Selecciona Python 3.13 para el hospedaje en Render. |
| `render.yaml` | Configuración de hospedaje con SQLite persistente en Render. |

Las rutas son `GET /` para consultar, `POST /users` para registrar y `GET /health` para verificar que la app puede consultar SQLite. El parámetro `page` de la consulta también se valida. La escritura nunca se realiza mediante un enlace `GET`.

## 3. Medidas de seguridad

| Requisito | Implementación | Dónde revisarlo |
| --- | --- | --- |
| Validación de entradas | Se comprueban campos, formato, longitud y rango en el servidor. Los controles HTML ayudan al usuario, pero no son la barrera de seguridad. | `validation.py`, `app.py` |
| Normalización y sanitización razonable | Se normaliza Unicode y se unifican espacios según el campo; después se rechaza lo que incumple las reglas. | `validation.py` |
| Protección frente a inyección SQL | Los valores se envían mediante parámetros `?`, separados del texto de las consultas. | `db.py` |
| Codificación de salida | Jinja escapa los valores al insertarlos en HTML; no se marca entrada de usuarios como HTML seguro. | `templates/` |
| Manejo seguro de errores | Respuestas públicas controladas; los errores inesperados incluyen una referencia sin revelar consultas, rutas ni trazas. | `app.py`, `templates/` |
| Reutilización segura | Una sola implementación de las reglas y una capa común de acceso a datos; las rutas las llaman. | `validation.py`, `db.py`, `app.py` |
| Eliminación de código muerto | Se entrega únicamente el flujo utilizado, sus utilidades, plantillas y pruebas. No hay rutas antiguas, funciones vulnerables de demostración ni bloques comentados de versiones anteriores. | Todo el proyecto |
| Protección CSRF | Flask-WTF valida un token asociado a la sesión en las solicitudes de escritura. | `app.py`, `templates/` |
| Límites y defensas del navegador | Peticiones de hasta 8 KiB, listado paginado y cabeceras CSP, `nosniff`, protección contra marcos y política de referencias. | `app.py` |

### Validación no significa “borrar cualquier cosa sospechosa”

- **Nombre:** Unicode NFC, espacios exteriores eliminados y espacios consecutivos unificados. Admite letras Unicode y marcas combinantes, espacios, apóstrofes, guiones y puntos; longitud de 2 a 80 caracteres. Por ejemplo, `  María   O'Connor  ` se guarda como `María O'Connor`. Esta regla escolar puede excluir nombres reales; se debe adaptar al dominio de una aplicación real.
- **Correo:** validación con `email-validator`, sin comprobaciones DNS ni envío de mensajes. Se normaliza y se guarda en minúsculas para que la regla de unicidad del ejercicio sea sencilla. Convertir toda la dirección a minúsculas es una decisión de este proyecto, no una regla universal para todos los sistemas de correo. La parte local no admite caracteres SMTPUTF8.
- **Edad:** solamente dígitos ASCII, convertidos a entero, entre 0 y 120 inclusive. No se aceptan decimales, números negativos o texto.
- **Estructura:** se rechazan datos ausentes, campos inesperados o repetidos y solicitudes que no correspondan al formulario esperado. Los límites se aplican también si alguien modifica el HTML o envía la petición con otra herramienta.

No se borran etiquetas o fragmentos SQL para transformar una entrada peligrosa en otra distinta. Se acepta el formato permitido o se informa el error. Normalizar facilita validar; no reemplaza la validación, los parámetros SQL ni el escape de salida.

### SQL, HTML y errores: controles diferentes

Las consultas de `db.py` mantienen el SQL fijo y pasan los datos aparte. Un apóstrofe en `O'Connor` se trata como dato, no como parte de una instrucción. Las restricciones de SQLite refuerzan la integridad, incluida la unicidad del correo. No se concatenan valores de formularios para construir SQL.

Al mostrar datos, el escape de Jinja transforma los caracteres con significado HTML. Esta protección corresponde al contexto HTML: si se agregaran JavaScript, URLs dinámicas u otros contextos, habría que diseñar la codificación apropiada para ellos. La política CSP complementa el escape y permite únicamente los recursos necesarios.

Las cookies de sesión usan `HttpOnly` y `SameSite=Lax`; en producción también usan `Secure` y requieren HTTPS. La cookie sostiene la protección del formulario, no representa una autenticación de usuario.

| Situación | Respuesta |
| --- | --- |
| Datos con formato o rango incorrecto | `422`, con errores de los campos. |
| Correo ya registrado | `409`, con explicación comprensible. |
| Token CSRF ausente/no válido o estructura incorrecta | `400`, con mensaje seguro. |
| Solicitud que excede 8 KiB | `413`. |
| Recurso inexistente | `404`. |
| Error interno inesperado | `500`, con mensaje genérico y referencia. |

El registro interno de errores inesperados contiene la referencia y datos de diagnóstico limitados, sin valores personales del formulario ni el mensaje crudo de la excepción. El depurador no se expone al visitante.

## 4. Comprobarlo para la actividad

Las siguientes pruebas son para **tu copia local**. En el navegador puedes ver los códigos HTTP en Herramientas de desarrollador → Red/Network; un guardado correcto redirige al listado.

1. **Registro normal y persistencia.** Registra `Ana López`, `ana@example.com`, `20`. Comprueba el listado, detén el servidor y vuelve a iniciarlo: el registro debe seguir presente.
2. **Normalización.** Registra `  María   O'Connor  `, `MARIA@example.com`, `21`. El listado debe mostrar espacios unificados y correo en minúsculas. Intenta registrar el mismo correo con otra combinación de mayúsculas: debe devolver `409`.
3. **Validación en el servidor.** Prueba un correo `sin-arroba` o edad `121`. El navegador puede detener el envío; para probar al servidor, abre el inspector del formulario y agrega el atributo `novalidate`. Al enviar, la aplicación debe responder `422` sin insertar el registro.
4. **Entrada SQL.** Con un correo ficticio nuevo y edad válida, escribe en nombre `Robert'); DROP TABLE users;--`. Debe rechazarse por las reglas del nombre y el listado debe continuar disponible. El nombre permitido `O'Connor` debe funcionar. La prueba automatizada de acceso a datos comprueba además los parámetros directamente, sin depender de que la validación bloquee la cadena.
5. **Entrada HTML/XSS.** Escribe `<script>alert(1)</script>` como nombre. Debe rechazarse sin ejecutar código. El valor que vuelva a mostrarse en el formulario se escapa. Las pruebas comprueban también el escape de datos al renderizar para verificar esa defensa por separado.
6. **CSRF.** Recarga la página. En el inspector HTML, elimina el campo oculto llamado `csrf_token`; rellena datos válidos y envía. Debe responder `400` y no registrar el usuario. Recarga para recuperar un formulario válido.
7. **Errores seguros.** Visita `/no-existe` y verifica la página `404`. Ejecuta la suite siguiente: el caso de error interno simula una falla controlada y verifica el `500` genérico sin divulgar información interna. No hace falta dañar la base ni agregar una ruta vulnerable para la demostración.

### Pruebas automatizadas

En Windows, desde la carpeta del proyecto:

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

En macOS/Linux:

```bash
.venv/bin/python -m unittest discover -s tests -v
```

La suite usa bases de datos temporales para probar controles y casos de error sin modificar los registros de tu demostración. La salida final debe indicar `OK`. Puedes entregar capturas del registro normal, la normalización, un rechazo de validación y el resultado de las pruebas, acompañadas de la tabla de medidas anterior.

**Verificación de esta entrega:** 25 pruebas aprobadas en Windows con Python 3.13.2 y las versiones de dependencias indicadas. También se comprobó un registro real desde el navegador y su normalización en el listado. El despliegue en Render se documentó, pero no se ejecutó.

Para ejecutar únicamente la simulación de error interno en Windows:

```powershell
.\.venv\Scripts\python.exe -m unittest tests.test_app.SecureApplicationTests.test_internal_database_error_does_not_expose_internal_details_or_personal_data -v
```

Esta prueba reemplaza temporalmente una consulta por una excepción simulada y revisa la respuesta `500`; el código real no cambia.

## 5. Hospedar públicamente en Render

La entrega incluye los archivos y las instrucciones; no crea una cuenta, no publica automáticamente y no contrata recursos. Las instrucciones se contrastaron con documentación oficial el **12 de septiembre de 2026**.

### Opción A: conservar los registros entre reinicios

`render.yaml` configura un servicio Python de pago con un disco persistente de 1 GB montado en `/var/data`. Render solo conserva los archivos escritos dentro del punto de montaje; por eso `DATABASE_PATH` apunta a `/var/data/users.sqlite3`. Sin disco, el sistema de archivos es efímero. [Documentación oficial de discos persistentes](https://render.com/docs/disks).

1. Crea un repositorio en GitHub y sube **el contenido** de `software-seguro`, dejando `app.py`, `requirements.txt` y `render.yaml` en la raíz. Incluye los archivos de configuración de ejemplo. No subas `.env`, `.venv` ni tu base local.
2. Entra al [panel de Render](https://dashboard.render.com/), selecciona **New → Blueprint** y conecta ese repositorio. Si Render solicita autorización de GitHub, permite el acceso al repositorio que elegiste.
3. Selecciona la rama y confirma que Render lee `render.yaml`. Revisa la lista de recursos y el costo que muestra antes de elegir **Deploy Blueprint**. Este es el flujo documentado para crear un Blueprint. [Guía oficial de Blueprints](https://render.com/docs/infrastructure-as-code).
4. El archivo configura `APP_ENV=production`, genera `SECRET_KEY`, usa el plan `0.5c-512mb`, una instancia y el disco. El identificador de plan corresponde a la documentación consultada; revisa la oferta vigente del panel antes de aceptar. `generateValue: true` crea un secreto aleatorio al crear la variable. [Referencia oficial de `render.yaml`](https://render.com/docs/blueprint-spec).
5. Espera a que el despliegue figure como activo. Abre la dirección HTTPS `*.onrender.com` que aparece en el servicio y prueba el registro con datos ficticios. La receta Flask de Render utiliza instalación desde `requirements.txt` y Gunicorn. [Guía oficial para Flask](https://render.com/docs/deploy-flask).
6. Comprueba `/health`: debe responder correctamente. Registra un usuario ficticio, realiza un despliegue manual desde el panel y verifica que sigue en el listado. Si desaparece, comprueba el montaje y `DATABASE_PATH`.

El comando de inicio incluido es:

```bash
gunicorn --workers 1 --threads 4 --bind 0.0.0.0:$PORT app:app
```

Render proporciona `PORT`, enruta las peticiones al servicio y ofrece HTTPS. `0.0.0.0` permite que la plataforma acceda al servidor. [Documentación oficial de servicios web](https://render.com/docs/web-services).

El archivo `.python-version` selecciona la serie 3.13; Render permite omitir el número de parche y utiliza el último correspondiente. [Configuración oficial de la versión de Python](https://render.com/docs/python-version).

La tabla se crea al iniciar la aplicación, cuando el disco ya está disponible. No se crea durante el build: Render no monta el disco persistente en esa fase. Un disco solo puede estar conectado a una instancia, y los despliegues con disco pueden interrumpir brevemente el servicio. [Limitaciones oficiales de los discos](https://render.com/docs/disks).

### Opción B: demostración gratuita con datos temporales

Antes de crear el servicio, modifica `render.yaml`:

- Cambia `plan: 0.5c-512mb` por `plan: free`.
- Elimina todo el bloque `disk` (nombre, ruta y tamaño incluidos).
- Cambia el valor de `DATABASE_PATH` a `/tmp/users.sqlite3`.
- Conserva `APP_ENV=production`, la generación de `SECRET_KEY` y el comando Gunicorn.

Después sigue el flujo de Blueprint anterior y revisa el resumen del panel. Los servicios gratuitos no admiten discos persistentes; la base SQLite se pierde al reiniciar, volver a desplegar o suspenderse el servicio. Además, pueden suspenderse tras un periodo de inactividad y tardar en volver a responder. Esta variante sirve para mostrar el proyecto y acepta que los registros sean temporales. [Condiciones y límites oficiales del servicio gratuito](https://render.com/docs/free).

### Solución de problemas

| Síntoma | Qué comprobar |
| --- | --- |
| Windows impide crear `.venv` o `instance` en Documentos | Extrae el proyecto en una ubicación donde Python tenga permiso de escritura. También puedes establecer `DATABASE_PATH` en una ruta permitida para la base de datos. No necesitas desactivar las protecciones del equipo. |
| Render no encuentra `app` o `requirements.txt` | Sube los archivos a la raíz del repositorio o configura correctamente la carpeta raíz del servicio. |
| El inicio falla por la clave | En producción debe existir `SECRET_KEY`, aleatoria y con al menos 32 caracteres. No reutilices una clave publicada. |
| CSRF falla después de reiniciar localmente | Recarga el formulario; configura una clave local estable si quieres conservar las sesiones. |
| CSRF falla al probar producción con HTTP local | Las cookies `Secure` requieren HTTPS; usa `development` en la prueba local y la URL HTTPS en Render. |
| No se guardan los registros públicos | Comprueba que exista el disco y que la base esté dentro de `/var/data`; la variante gratuita es temporal. |
| Error `500` o `/health` falla | Busca la referencia en los registros del servidor y comprueba acceso a la ruta de SQLite. No actives el depurador en el servicio público. |

## 6. Alcance y mantenimiento

Este registro escolar es pequeño y público. No incluye autenticación, roles, verificación de correo, límite de registros por visitante ni protección específica contra altas automatizadas. CSRF evita ciertos envíos desde otro sitio; no impide que un visitante complete el formulario repetidamente. Para usar datos reales o abrir un servicio estable habría que definir permisos, privacidad, retención, controles contra abuso y copias de seguridad según ese uso.

SQLite y una sola instancia simplifican la actividad. Si se necesitara escalar a varias instancias, habría que adaptar la capa de datos para una base compartida, como PostgreSQL. El disco persistente conserva archivos, pero la estrategia de respaldo y restauración debe verificarse antes de depender de los registros.

Mantén las dependencias actualizadas y vuelve a ejecutar las pruebas después de cambios. Para evitar código muerto en futuras versiones, elimina también las rutas, importaciones, plantillas y configuraciones que dejen de tener un uso. Las pruebas activas y la documentación son parte del mantenimiento; no son código muerto.
