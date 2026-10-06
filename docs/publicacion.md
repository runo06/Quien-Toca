# Publicación (plan gratuito)

```
Visitante ──► Cloudflare Workers (React)  ──fetch /api──►  Render (Django + gunicorn)  ──►  Neon (PostgreSQL)
                                                                                           ▲
GitHub Actions ── cada noche: importar_ticketmaster ───────────────────────────────────────┘
```

## Límites gratuitos (revisados el 5 de octubre de 2026)

| Servicio | Lo que da gratis | Lo que hay que saber |
|---|---|---|
| **Neon** | 1 GB por proyecto, 100 CU-horas al mes, 5 GB de transferencia | Se suspende tras 5 min sin uso (despierta en menos de un segundo). Permanente, sin tarjeta. |
| **Render** | 750 horas de instancia al mes, 512 MB de memoria | Se duerme tras 15 min sin visitas y tarda ~1 min en despertar. Sin consola (shell) ni pre-deploy. Su PostgreSQL gratis caduca a los 30 días: por eso la base va en Neon. |
| **Cloudflare Workers** | Archivos estáticos gratis e ilimitados; 100,000 peticiones al día al código del Worker (este proyecto no tiene código, solo archivos) | Un build a la vez. |
| **GitHub Actions** | Repositorio privado: 2,000 minutos al mes. Público: ilimitado | En repositorios **públicos** los workflows programados se apagan tras 60 días sin actividad. |

Fuentes: [neon.com/pricing](https://neon.com/pricing),
[render.com/docs/free](https://render.com/docs/free),
[Cloudflare Workers: archivos estáticos](https://developers.cloudflare.com/workers/static-assets/billing-and-limitations/),
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

## 3. Frontend en Cloudflare Workers

Cloudflare ya crea los proyectos nuevos como **Workers** (Pages quedó escondido).
Workers sirve los archivos del build igual de gratis; la configuración vive en el repositorio:

- [`frontend/wrangler.jsonc`](../frontend/wrangler.jsonc): publica `dist` y manda cualquier
  dirección (`/cdmx`, `/concierto/...`) a `index.html` para que React Router decida.
- [`frontend/.env.production`](../frontend/.env.production): `VITE_API_URL`, la dirección del backend
  (no es secreta). Si cambia el dominio de Render, cámbiala aquí.
- [`frontend/.node-version`](../frontend/.node-version): Node 24 para el build.

1. Crea una cuenta en [dash.cloudflare.com](https://dash.cloudflare.com).
2. **Workers & Pages > Create > Import a repository** y elige el repositorio.
3. Llena el formulario:

   | Campo | Valor |
   |---|---|
   | Project name | `quien-toca` (igual que `name` en `wrangler.jsonc`) |
   | Build command | `npm run build` |
   | Deploy command | `npx wrangler deploy` (ya viene) |
   | Preview command | lo que venga |
   | Advanced settings > Path | `frontend` |
   | API token | el que propone |
   | Variables | ninguna |

4. **Deploy**. Al terminar tendrás `https://quien-toca.<tu-subdominio>.workers.dev`.

## 4. Conectar frontend y backend (CORS)

En Render > tu servicio > **Environment**, pon
`CORS_ORIGENES_PERMITIDOS` = la dirección `https://quien-toca.<tu-subdominio>.workers.dev` (sin `/` al final) y guarda;
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
| La página dice "No pudimos conectar" en todo | `VITE_API_URL` mal escrita en `frontend/.env.production`, o falta el origen en `CORS_ORIGENES_PERMITIDOS` (en la consola del navegador aparece "CORS") |
| Render responde 400 Bad Request | El dominio no está en `ALLOWED_HOSTS`; se agrega solo con `RENDER_EXTERNAL_HOSTNAME`, revisa que no lo hayas sobrescrito |
| El panel `/admin` se ve sin estilos | Falló `collectstatic` en el build: revisa el log de Render |
| El workflow nocturno falla | Revisa los secretos; el log muestra el mensaje del comando |
