# Muse Estudios — paquete privado de seguimiento académico

Paquete para compartir con invitación individual una adaptación de las alertas académicas UVA / grado superior. No contiene datos ni credenciales de Javier.

## Qué incluye

- `muse/SKILL.md`: instrucciones en español para que cada persona configure Muse con sus propios estudios y consulte un calendario académico mediante el conector de calendario integrado, en modo lectura.
- `campus_tasks.py`: alternativa CLI independiente para leer feeds iCalendar fuera de Muse. Usa solo la biblioteca estándar de Python, valida HTTPS, mantiene estado local y ofrece `--list`, `--json` y `--check` con avisos de tarea nueva/cambiada y umbrales de 7/3/1 días.
- `config.example.json`: plantilla vacía, sin URLs ni tokens reales.
- `tests/`: pruebas automáticas del parser, los avisos y el tratamiento de enlaces privados.

## Estado y compatibilidad con Muse

Meta describe Muse como una VM Linux personal persistente, con conectores, skills, CLIs y crons. Esta entrega usa una guía Markdown (`muse/SKILL.md`); **no es un perfil Hermes ni una importación nativa de Hermes**. Tampoco he podido probarla dentro de una cuenta/VM real de Muse. Para la primera prueba, hay que darle a Muse esa guía y comprobar que su conector de calendario ve el calendario académico correcto. La guía se detiene si no puede hacerlo de forma segura.

La parte reutilizada de la automatización actual es el seguimiento de fechas del calendario (novedades y recordatorios 7/3/1). No incluye todavía consultas directas de notas, foros, PDFs ni escritura en Obsidian; esos flujos requieren portarlos y validarlos por separado.

## Credenciales: importante

Una URL de calendario Moodle/iCalendar puede contener un token que funciona como credencial. Nunca subas una URL real, un `.ics`, un `config.json`, un `.env` ni el estado de tareas a GitHub.

El CLI independiente guarda la URL en `config.json`, que está en `.gitignore` y se restringe a permisos `0600` al cargarla. Eso protege frente a otros usuarios del sistema, **pero no la oculta de un agente que pueda leer ese mismo espacio de trabajo**. Por eso no se recomienda ejecutar el CLI con enlaces privados dentro de Muse. Para Muse, utiliza el conector de calendario integrado y no pegues enlaces/token de Moodle en el chat. Si el calendario no está disponible por ese conector, detente; no introduzcas la credencial en un fichero accesible al agente.

## Uso local del CLI (opcional; fuera de Muse)

1. Copia `config.example.json` como `config.json`.
2. Añade localmente tus propios enlaces HTTPS de calendario en `config.json`; no los mandes por chat ni los subas.
3. Ejecuta:

```bash
python3 campus_tasks.py --list
python3 campus_tasks.py --check
python3 campus_tasks.py --json
python3 -m unittest discover -s tests -v
```

El modo `--check` no imprime nada si no hay novedades ni un recordatorio nuevo. No desactiva la verificación TLS y no imprime URLs de feeds en errores o resultados.

## Compartir sin publicarlo

El repositorio debe mantenerse **privado**. Invita a cada amigo por su usuario GitHub, con permiso de solo lectura; no compartas una contraseña común ni envíes el enlace fuera de las invitaciones individuales. `LICENSE.txt` expresa el uso personal/no comercial y prohíbe redistribuir o vender el material.

Esto controla quién accede inicialmente, pero no puede impedir que una persona autorizada copie el contenido. Revocar el acceso no borra copias descargadas, capturas ni archivos ya importados a su propia VM.

## Referencias oficiales

- [Meta AI Research — How We Built Safety Into Muse](https://research.meta.ai/blog/security-and-safety-for-ai-agents-our-approach-with-muse): descripción de VM, conectores, skills, crons y límites de seguridad.
- [Muse — Your Personal AI Agent](https://muse.ai/): información general del producto y sus conectores.
