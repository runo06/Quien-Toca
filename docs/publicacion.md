# Publicación (plan gratuito)

```
Visitante ──► Cloudflare Pages (React)  ──fetch /api──►  Render (Django + gunicorn)  ──►  Neon (PostgreSQL)
                                                                                           ▲
GitHub Actions ── cada noche: importar_ticketmaster ───────────────────────────────────────┘
```

## Límites gratuitos (revisados el 5 de octubre de 2026)

| Servicio | Lo que da gratis | Lo que hay que saber |
|---|---|---|
| **Neon** | 1 GB por proyecto, 100 CU-horas al mes, 5 GB de transferencia | Se suspende tras 5 min sin uso (despierta en menos de un segundo). Permanente, sin tarjeta. |
| **Render** | 750 horas de instancia al mes, 512 MB de memoria | Se duerme tras 15 min sin visitas y tarda ~1 min en despertar. Sin consola (shell) ni pre-deploy. Su PostgreSQL gratis caduca a los 30 días: por eso la base va en Neon. |
| **Cloudflare Pages** | 500 builds al mes, 20,000 archivos, sin límite de tráfico publicado | Un build a la vez, máximo 20 min. |
| **GitHub Actions** | Repositorio privado: 2,000 minutos al mes. Público: ilimitado | En repositorios **públicos** los workflows programados se apagan tras 60 días sin actividad. |

Fuentes: [neon.com/pricing](https://neon.com/pricing),
[render.com/docs/free](https://render.com/docs/free),
[Cloudflare Pages limits](https://developers.cloudflare.com/pages/platform/limits/),
[GitHub Actions billing](https://docs.github.com/en/billing/concepts/product-billing/github-actions).
Vuelve a revisarlos antes de publicar: cambian sin aviso.

## 1. Base de datos en Neon

1. Crea una cuenta en [neon.com](https://neon.com) (con GitHub, sin tarjeta).
2. **New project**: nombre `quien-toca`, PostgreSQL 17, región **AWS US East 2 (Ohio)**
   (la misma zona que Render en Ohio: menos latencia).
3. En **Connect**, desactiva **Connection pooling** y copia la cadena. Se ve así:
   `postgresql://usuario:clave@ep-xxxx.us-east-2.aws.neon.tech/neondb?sslmode=require&channel_binding=require`.
   Es tu `DATABASE_URL` de producción; guárdala en un lugar seguro.

   Se usa la conexión directa (sin `-pooler`) porque Django mantiene sus propias
   conexiones abiertas (`conn_max_age`).
4. Crea las tablas y tu usuario del panel desde tu equipo (Render gratis no tiene consola).
   En PowerShell, con la cadena entre comillas simples:

   ```powershell
   $neon = 'postgresql://...'
   docker compose run --rm -e DATABASE_URL=$neon backend python manage.py migrate
   docker compose run --rm -e DATABASE_URL=$neon backend python manage.py createsuperuser
   docker compose run --rm -e DATABASE_URL=$neon backend python manage.py importar_ticketmaster
   ```

## 2. Backend en Render

1. Crea una cuenta en [render.com](https://render.com) con GitHub y dale acceso al repositorio.
2. **New > Blueprint**, elige el repositorio. Render lee [`render.yaml`](../render.yaml) y te pide:
   - `DATABASE_URL`: la cadena de Neon.
   - `TICKETMASTER_API_KEY`: tu clave (no la usa el servidor hoy, pero así queda lista).
   - `CORS_ORIGENES_PERMITIDOS`: déjalo vacío por ahora; lo llenas en el paso 4.
   `DJANGO_SECRET_KEY` la genera Render sola.
3. Espera el primer deploy (instala, junta estáticos y migra). Prueba:
   `https://quien-toca-api.onrender.com/api/salud/` debe responder `{"ok": true}`.
   Si Render le puso otro nombre al servicio, usa el tuyo en los pasos siguientes.

## 3. Frontend en Cloudflare Pages

1. Crea una cuenta en [dash.cloudflare.com](https://dash.cloudflare.com).
2. **Workers & Pages > Create > Pages > Import an existing Git repository**.
   (Cuidado: la opción por defecto es *Workers*; elige la pestaña **Pages**.)
3. Configuración del build:

   | Campo | Valor |
   |---|---|
   | Production branch | `main` |
   | Framework preset | React (Vite) |
   | Build command | `npm run build` |
   | Build output directory | `dist` |
   | Root directory | `frontend` |

4. Variables de entorno (se usan **al compilar**; si cambian, vuelve a desplegar):
   - `VITE_API_URL` = `https://quien-toca-api.onrender.com/api`
   - `NODE_VERSION` = `24`
5. Al terminar tendrás `https://quien-toca.pages.dev` (o el nombre que te asigne).
   Las rutas como `/cdmx` funcionan solas: sin `404.html`, Pages sirve
   `index.html` para cualquier dirección y React Router decide qué mostrar.

## 4. Conectar frontend y backend (CORS)

En Render > tu servicio > **Environment**, pon
`CORS_ORIGENES_PERMITIDOS` = `https://quien-toca.pages.dev` (sin `/` al final) y guarda;
Render se vuelve a publicar solo. Si después usas un dominio propio, agrégalo separado por coma.

## 5. GitHub Actions

En GitHub > el repositorio > **Settings > Secrets and variables > Actions > New repository secret**:

| Secreto | Valor |
|---|---|
| `DATABASE_URL` | la cadena de Neon |
| `TICKETMASTER_API_KEY` | tu clave de Ticketmaster |

- [`pruebas.yml`](../.github/workflows/pruebas.yml) corre en cada push: pruebas con
  PostgreSQL, migraciones al día, `check --deploy` y build del frontend.
- [`importar.yml`](../.github/workflows/importar.yml) importa cada noche a las 3:00 a. m.
  (hora de Ciudad de México). Para probarlo ya: **Actions > Importar conciertos > Run workflow**.

## Si algo falla

| Síntoma | Causa probable |
|---|---|
| La página dice "No pudimos conectar" en todo | `VITE_API_URL` mal escrita, o falta el origen en `CORS_ORIGENES_PERMITIDOS` (en la consola del navegador aparece "CORS") |
| Render responde 400 Bad Request | El dominio no está en `ALLOWED_HOSTS`; se agrega solo con `RENDER_EXTERNAL_HOSTNAME`, revisa que no lo hayas sobrescrito |
| El panel `/admin` se ve sin estilos | Falló `collectstatic` en el build: revisa el log de Render |
| El workflow nocturno falla | Revisa los secretos; el log muestra el mensaje del comando |
