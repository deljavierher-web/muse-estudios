# Muse Estudios — Paquete de Asistencia Académica y Automatización Moodle

Paquete diseñado para adaptar de forma segura, privada y reutilizable las automatizaciones académicas universitarias y de formación profesional (Moodle UVA y Educacyl) para **Meta Muse** y ejecución local.

**Cero Credenciales:** No contiene datos personales, calificaciones, cursos fijos ni credenciales de Javier.

---

## 📦 Estructura del Paquete

```text
muse-estudios/
├── LICENSE.txt                     # Licencia de uso personal educativo no comercial
├── README.md                       # Documentación principal del repositorio
├── moodle_cli.py                   # CLI completo de conexión con Moodle (UVa + Educacyl)
├── moodle_manager.py               # Motor genérico de autenticación SAML/ADFS y scraping
├── moodle_creds.example.json       # Plantilla de credenciales para Moodle
├── campus_tasks.py                 # Parser CLI de iCalendar (Python estándar)
├── config.example.json             # Plantilla vacía para feeds iCalendar
├── docs/
│   ├── PLAN_MUSE_COMPLETO.md       # Auditoría técnica y plan maestro de arquitectura
│   ├── ARQUITECTURA_COMERCIAL_Y_PROTECCION.md # Modelo de protección y hoja de ruta SaaS
│   └── GUIA_CONEXION_CAMPUS.md     # Guía visual para conectar Moodle con Google Calendar
├── muse/
│   ├── LAUNCHER_PROMPT.md          # Prompt único para activar el Asistente en Meta Muse
│   ├── INSTRUCCIONES_MUSE.md       # Prompt extendido con motor proactivo de tareas
│   ├── GUIA_USUARIO_MOVIL.md       # Guía rápida de 3 pasos para el alumno
│   ├── SKILL.md                    # Especificación técnica base del asistente
│   └── modulos/
│       ├── analisis_practicas.md   # Módulo para analizar enunciados y PDFs de prácticas
│       └── seguimiento_tareas.md   # Módulo de planificación y ventanas de urgencia
└── tests/
    ├── test_campus_tasks.py        # Pruebas unitarias del parser, alertas y permisos
    └── test_sanitizacion.py        # Pruebas de detección de fugas de datos sensibles
```

---

## 🚀 Opciones de Uso

### Opción 1: En Meta Muse Móvil (Vía Prompt)
Pega el bloque de [`muse/LAUNCHER_PROMPT.md`](muse/LAUNCHER_PROMPT.md) en un chat nuevo de Meta Muse en tu móvil. El asistente te pedirá tu clave de activación, se conectará a tu calendario y te ofrecerá resolver tus prácticas de forma proactiva.

### Opción 2: Motor Completo de Moodle CLI (Tareas, Notas, PDFs y Apuntes)
Si quieres interactuar directamente con Moodle (UVa o Educacyl) como en Hermes:
1. Copia `moodle_creds.example.json` como `moodle_creds.json`:
   ```bash
   cp moodle_creds.example.json moodle_creds.json
   ```
2. Rellena tu usuario y contraseña institucional en `moodle_creds.json` (el archivo está ignorado en git por seguridad).
3. Ejecuta los comandos:
   ```bash
   python3 moodle_cli.py tasks            # Lista tareas y plazos de entrega
   python3 moodle_cli.py grades           # Consulta calificaciones de tus asignaturas
   python3 moodle_cli.py task-detail 1234 # Extrae enunciado y texto de PDFs de la tarea
   python3 moodle_cli.py forums           # Revisa comunicados docentes en foros
   python3 moodle_cli.py sync-resources   # Escanea y descarga apuntes organizados a disco
   ```

### Opción 3: Vigilante Ligero de Calendario (iCalendar)
```bash
python3 campus_tasks.py --list    # Lista todas las tareas futuras del calendario
python3 campus_tasks.py --check   # Comprueba alertas silenciosas (7d, 3d, 1d)
python3 campus_tasks.py --json    # Emite tareas en JSON limpio sin URLs
```

---

## 🛡️ Seguridad y Verificación Continua

* **Protección de Datos:** Las credenciales y estados locales nunca se suben al repositorio (`.gitignore`).
* **Suite de Sanitización:** Todo el repositorio se escanea continuamente para asegurar que ninguna clave, token ni ruta privada quede expuesta:
  ```bash
  python3 -m unittest discover tests -v
  ```

---

## 📚 Referencias Oficiales
* [Meta AI Research — How We Built Safety Into Muse](https://research.meta.ai/blog/security-and-safety-for-ai-agents-our-approach-with-muse): Arquitectura de Secure VMs, conectores nativos y sandboxing.
* [RFC 5545 — Internet Calendaring and Scheduling (iCalendar)](https://datatracker.ietf.org/doc/html/rfc5545).
