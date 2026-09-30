# Muse Estudios — Paquete Privado de Asistencia Académica para Meta Muse

Paquete diseñado para compartir mediante invitación individual una adaptación segura, privada y reutilizable de las alertas y asistencia académica universitaria o de formación profesional para **Meta Muse**.

**Cero Credenciales:** No contiene datos personales, cursos ni credenciales de Javier.

---

## 📦 Estructura del Paquete

```text
muse-estudios/
├── LICENSE.txt                     # Licencia de uso personal educativo no comercial
├── README.md                       # Documentación principal del repositorio
├── config.example.json             # Plantilla vacía para ejecución local CLI
├── campus_tasks.py                 # Parser CLI independiente (Python estándar)
├── docs/
│   ├── PLAN_MUSE_COMPLETO.md       # Auditoría técnica y plan maestro de arquitectura
│   └── GUIA_CONEXION_CAMPUS.md     # Guía visual para conectar Moodle con Google Calendar
├── muse/
│   ├── INSTRUCCIONES_MUSE.md       # Prompt principal para configurar Meta Muse en el móvil
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

## 📱 Uso Rápido en Móvil (Meta Muse)

Para configurar tu asistente en Meta Muse sin usar terminal ni editar archivos:

1. **Sincroniza tu calendario de clase:** Sigue [`docs/GUIA_CONEXION_CAMPUS.md`](docs/GUIA_CONEXION_CAMPUS.md) para añadir tu feed de Moodle a Google Calendar o Microsoft Outlook.
2. **Conecta tu calendario a Muse:** En la app de Meta Muse, activa el conector oficial de **Google Calendar** (o Outlook) en modo lectura.
3. **Inicia el asistente:** Sigue [`muse/GUIA_USUARIO_MOVIL.md`](muse/GUIA_USUARIO_MOVIL.md) y envía a Muse el contenido de [`muse/INSTRUCCIONES_MUSE.md`](muse/INSTRUCCIONES_MUSE.md). Responde a las 4 preguntas breves de bienvenida y tu tutor estará listo.

---

## 💻 Uso Local del CLI (Opcional, en tu Ordenador)

Si prefieres ejecutar el seguimiento desde tu propia terminal fuera de Muse:

1. Copia `config.example.json` como `config.json`.
2. Añade tus enlaces HTTPS de calendario en `config.json`.
3. Comprueba y ejecuta:
   ```bash
   python3 campus_tasks.py --list    # Lista todas las tareas futuras
   python3 campus_tasks.py --check   # Comprueba alertas (silencio si no hay novedades)
   python3 campus_tasks.py --json    # Emite tareas en JSON limpio sin URLs
   ```

El archivo `config.json` se protege automáticamente con permisos `0600` (solo legible por tu usuario) y está ignorado en `.gitignore`.

---

## 🛡️ Seguridad y Privacidad

* **Nunca pegues contraseñas ni URLs con tokens en el chat:** Los enlaces iCalendar contienen un `authtoken` privado. Al sincronizar a través de Google Calendar y usar el conector de Muse, la IA solo lee eventos limpios sin tocar tus claves.
* **Protección contra Inyección de Prompts:** Las descripciones de tareas y los archivos PDF subidos se tratan estrictamente como datos pasivos, neutralizando cualquier intento de alterar las instrucciones del asistente.
* **Validación Continua:** El repositorio cuenta con una suite de pruebas que verifica la sanitización de URLs y la ausencia de datos privados:
  ```bash
  python3 -m unittest discover tests -v
  ```

---

## 🔒 Compartir sin Publicarlo

El repositorio debe mantenerse **estrictamente privado**. Invita a cada amigo con acceso de solo lectura individual a través de su usuario de GitHub.

> [!WARNING]
> La licencia [`LICENSE.txt`](LICENSE.txt) expresa los términos legales de uso personal y prohíbe la redistribución o venta. No obstante, ten en cuenta que ninguna medida técnica puede impedir que una persona autorizada copie o reenvíe material que ya haya recibido en su dispositivo.

---

## 📚 Referencias Oficiales
* [Meta AI Research — How We Built Safety Into Muse](https://research.meta.ai/blog/security-and-safety-for-ai-agents-our-approach-with-muse): Arquitectura de Secure VMs, conectores nativos y sandboxing.
* [RFC 5545 — Internet Calendaring and Scheduling (iCalendar)](https://datatracker.ietf.org/doc/html/rfc5545).
