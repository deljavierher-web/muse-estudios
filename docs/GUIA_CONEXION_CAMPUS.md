# Guía de Conexión Segura del Campus Virtual a Meta Muse

Esta guía explica cómo conectar las tareas y entregas de tu campus virtual (Moodle UVA, Educacyl o cualquier Moodle) con Meta Muse en tu teléfono móvil **de forma 100% segura, sin revelar contraseñas ni tokens privados a ninguna IA**.

---

## ⚠️ Regla de Oro de Seguridad

> [!CAUTION]
> **NUNCA pegues el enlace de tu calendario de Moodle ni tus contraseñas en el chat de Meta Muse.**  
> El enlace de exportación de Moodle contiene un parámetro llamado `authtoken` que actúa como una llave privada de lectura de tu cuenta. Si lo pegas en un chat, la clave queda almacenada en el historial del modelo.

El método seguro consiste en **conectar Moodle con Google Calendar (o Outlook)** y después **conectar Google Calendar con Meta Muse** usando la integración oficial. De este modo, Meta Muse solo lee eventos limpios y tus claves nunca salen de Google.

---

## Paso 1: Obtener la URL de suscripción en Moodle

1. Entra a tu **Campus Virtual** (ej. Campus Virtual UVA o Aula Virtual Educacyl) desde tu navegador web.
2. Accede al apartado **Calendario** (suele estar en el menú lateral o en tu *Área personal*).
3. Desplázate hasta la parte inferior de la página del calendario y haz clic en el botón **"Exportar calendario"**.
4. Configura las opciones recomendadas:
   * **¿Qué eventos exportar?:** Selecciona *Todos los eventos*.
   * **Para qué periodo:** Selecciona *Eventos recientes y próximos* (o *Próximos 60 días* si está disponible).
5. Haz clic en el botón **"Obtener URL en el calendario"** (no en "Exportar" como archivo `.ics`).
6. Copia la dirección URL completa que aparece en pantalla (empieza por `https://.../calendar/export_execute.php?...`).

---

## Paso 2: Añadir el calendario a tu Google Calendar (o Outlook)

Para que el calendario se actualice automáticamente en tu móvil:

### Si usas Google Calendar (Recomendado):
1. Abre [Google Calendar](https://calendar.google.com) en tu navegador (si estás en el móvil, usa el modo escritorio en el navegador).
2. En la barra lateral izquierda, busca la sección **"Otros calendarios"** y pulsa en el botón **`+`**.
3. Selecciona **"Desde URL"**.
4. Pega la URL que copiaste de Moodle en el Paso 1.
5. *(Opcional)* Marca "Hacer que el calendario sea público" como **desmarcado** (privado).
6. Pulsa en **"Añadir calendario"**.
7. En los ajustes de ese nuevo calendario en Google Calendar, puedes renombrarlo a algo claro como *"Universidad - Entregas"* o *"FP - Tareas"*.

*(Nota: Google Calendar actualiza los calendarios por URL de forma automática varias veces al día).*

### Si usas Microsoft Outlook:
1. Abre [Outlook Calendar](https://outlook.live.com/calendar).
2. Haz clic en **"Agregar calendario"** -> **"Suscribirse desde la web"**.
3. Pega la URL de Moodle, dale un nombre y guarda los cambios.

---

## Paso 3: Conectar tu calendario con Meta Muse en tu móvil

Ahora que tus tareas están en tu calendario personal seguro:

1. Abre la app de **Meta Muse** en tu teléfono móvil.
2. Ve a los **Ajustes** de tu asistente o pulsa en el icono de **Conectores / Integraciones**.
3. Localiza la integración de **Google Calendar** (o Outlook) y pulsa en **Conectar / Autorizar**.
4. Inicia sesión con tu cuenta de Google y concede permisos de **lectura de eventos**.
5. ¡Listo! Meta Muse ya puede consultar tus plazos y fechas límite sin haber tocado ninguna credencial ni token sensible.

---

## Paso 4: Iniciar el seguimiento con Muse

Abre una conversación con Meta Muse y copia el texto del archivo `muse/INSTRUCCIONES_MUSE.md` (o adjunta el archivo si la app lo permite). Muse te hará 4 preguntas breves para adaptarse a tu curso y comenzará a ayudarte con tus estudios.
