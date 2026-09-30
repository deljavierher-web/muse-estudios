# Arquitectura Comercial, Control de Acceso y Protección Anti-Copia

**Autor:** Javier Delgado Hernández / Auditoría de Arquitectura de Software  
**Propósito:** Definir el modelo de protección, entrega por invitación y hoja de ruta para la comercialización del asistente académico.

---

## 1. La Visión y el Desafío de Protección

El objetivo es trasladar la potencia del agente personal (Hermes) a una solución fácil de usar en el móvil para amigos y futuros clientes a través de **Meta Muse**, permitiendo:
1. **Monitorización de plazos:** Alertas automáticas de entregas.
2. **Resolución activa de tareas:** Preguntar al alumno *"¿Quieres que te haga esta tarea?"* y generar la solución técnica, código o memoria de laboratorio.
3. **Control de acceso y monetización:** Evitar que el sistema se copie o redistribuya sin permiso del autor.

---

## 2. Realidad Técnica: Niveles de Protección en Asistentes de IA

Para tomar decisiones informadas sobre la comercialización, es crucial entender qué protege cada tecnología y cuáles son sus límites reales:

```
+---------------------------------------------------------------------------------------+
| NIVEL 1: Control por Clave en el Prompt (Actual - Ideal para Amigos)                 |
| - Se exige una clave de activación (ej: VIP-CAMPUS-2026) antes de desbloquear.         |
| - Efectivo para el 95% de usuarios no técnicos.                                      |
| - Límite: Quien tenga el texto del prompt puede leerlo y compartirlo manualmente.    |
+---------------------------------------------------------------------------------------+
                                          |
                                          v
+---------------------------------------------------------------------------------------+
| NIVEL 2: Repositorio GitHub Privado (Control de Distribución)                        |
| - Solo los usuarios expresamente invitados por su usuario de GitHub acceden.          |
| - Permite revocar el acceso a actualizaciones con un solo clic.                      |
| - Límite: No borra copias locales ya descargadas o reenviadas por WhatsApp.          |
+---------------------------------------------------------------------------------------+
                                          |
                                          v
+---------------------------------------------------------------------------------------+
| NIVEL 3: Modelo SaaS / Backend Privado (Comercialización Profesional)                 |
| - La "receta secreta" (código y prompts) corre en tu propio servidor (Cloud Run/VPS).  |
| - Los estudiantes interactúan vía Bot de Telegram o Web App con login y suscripción.  |
| - Protección: 100% Hermética. Nadie puede ver ni copiar tus prompts ni tu código.     |
+---------------------------------------------------------------------------------------+
```

---

## 3. Estrategia de Entrega Inmediata (Fase 1: Amigos y Beta Testers)

Para compartirlo hoy mismo con amigos de confianza sin fricción y con control de acceso:

### A. Repositorio GitHub Privado
1. El proyecto se aloja en un repositorio **Privado** en tu cuenta de GitHub (`deljavierher-web/muse-estudios`).
2. Nadie en internet puede ver el código ni encontrarlo por buscador.
3. Si un amigo quiere tener acceso a las guías y actualizaciones, lo invitas como colaborador de solo lectura desde GitHub:  
   *Ajustes del Repositorio -> Collaborators -> Add people*.

### B. Sistema de Clave de Activación Personalizada
En el prompt [`muse/LAUNCHER_PROMPT.md`](../muse/LAUNCHER_PROMPT.md) hemos implementado una **Fase de Verificación de Licencia**:
* Muse le exige una contraseña antes de empezar.
* Puedes darle a cada amigo una clave personalizada para llevar el control de quién lo usa:
  * Amigo 1: `MUSE-CARLOS-2026`
  * Amigo 2: `MUSE-ALBERTO-2026`
  * Clave VIP general: `VIP-CAMPUS-2026`
* Esto genera una barrera psicológica y de acceso efectiva: tus amigos entenderán que es un software privado bajo licencia personal.

---

## 4. Hoja de Ruta para Monetización y Venta a Gran Escala (Fase 2)

Si tras probarlo con tus amigos ves que hay demanda y quieres **venderlo a otros estudiantes de la universidad o FP sin riesgo de que se copien el prompt**:

### Arquitectura Recomendada: "Campus Copilot SaaS"
1. **El Motor en la Nube (Backend):**
   * Creas una pequeña API en Python (FastAPI) alojada en Google Cloud Run (coste casi 0€/mes para poco tráfico).
   * La API contiene toda la lógica de Hermes: scraping seguro o conexión iCal, prompts avanzados de resolución de ejercicios y parsing de PDFs con modelos de lenguaje.
2. **La Interfaz del Estudiante:**
   * En lugar de entregarles el texto del prompt, los estudiantes interactúan a través de un **Bot de Telegram propio** (ej: `@CampusCopilotBot`) o una aplicación web móvil sencilla.
   * El alumno se registra, paga su cuota (ej. 4,99€/mes mediante Stripe) y recibe su token de acceso.
3. **Ventajas Absolutas:**
   * **Imposible de piratear:** El cliente solo ve las respuestas generadas y los avisos de entrega; nunca ve las instrucciones del sistema ni el código.
   * **Cancelación instantánea:** Si un alumno deja de pagar, su cuenta se bloquea inmediatamente desde la base de datos.
   * **Monetización recurrente:** Pagos mensuales automáticos.
