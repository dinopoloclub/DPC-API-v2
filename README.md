# DPC API v2
Version 2 of the DPC API (api.dinopoloclub.com/2/)
- Currently only supporting the diagnostics endpoints.

## Diagnostics

| What | Where |
| --- | --- |
| Turning posted form data into reports, handling uploads | [diagnostics/ingest.py](diagnostics/ingest.py) |
| Grouping errors into issues | [diagnostics/grouping.py](diagnostics/grouping.py) |
| The search box | [diagnostics/search.py](diagnostics/search.py) |
| Sign in with Slack | [diagnostics/slack.py](diagnostics/slack.py), [diagnostics/views/auth.py](diagnostics/views/auth.py) |
| Database tables | [diagnostics/models.py](diagnostics/models.py) |
| Game codes and display names | [diagnostics/games.py](diagnostics/games.py) |
| Pages | [diagnostics/views/](diagnostics/views/), [diagnostics/templates/diagnostics/](diagnostics/templates/diagnostics/) |
| Styles (Tailwind source) | [frontend/app.css](frontend/app.css) |
| Settings (all from environment variables) | [config/settings.py](config/settings.py), [.env.example](.env.example) |

# Administration
There isn't much exposed in the way of administration, but I have provided 2 scripts:<br/>
`docker compose exec web python manage.py prune_reports --days 180 [--dry-run]` - prune reports older than 180 days (including attachments)<br/>
`docker compose exec web python manage.py regroup_issues` - run the `grouping.py` rules over all issues/reports again, in case that you changed the rules.

# Deploying / Debugging
The app is run in a docker container on `istanbul`. You will need an account set up to deploy / view logs, and your account must be added to `apiv2-deployers` (`sudo usermod -aG api-deployers <username>`).<br/>
It pulls/clones from Github using a deployment SSH key scoped only to this repo, into the dir `/srv/apiv2/`.<br/>
Deployment is 'owned' by the user `apiv2`, so you should use `sudo -u apiv2 ....` for looking into the Docker container.<br/>
The docker container holds 2 volumes - one for postgres data, and one for uploads. These are persistent through deployments (unless you delete the volumes)<br/>

Example to browse the latest logs:
`sudo -u apiv2 docker compose --project-directory /srv/apiv2 logs -f --tail 100 web`

I have set up a script on the server to pull from git + redeploy which is in `/usr/local/bin/deploy-apiv2`, and can be run with `sudo -u apiv2 deploy-apiv2`
Traffic is routed via nginx using proxy_pass to the docker container, using the `/2/diagnostics` endpoint, and ratelimiting is applied.
The .env file is only existing on the server right now under `/srv/apiv2/.env` - which holds the necessary secrets.

# Local dev 
You can run the container locally by using a `.env` with `ENVIRONMENT` set to `dev`. This will keep you always logged in, and will connect to a local postgres deployment.<br/>
`docker compose -f docker-compose.yml -f docker-compose.dev.yml up -d db` as an example will run postgres locally<br/>
`uv sync` to install dependencies<br/>
`uv run --env-file .env manage.y migrate` will bootstrap the database if needed<br/>
`uv run tailwindcss -i frontend/app.cs -o diagnostics/static/diagnostics/app.css --watch` to build the css, and automatically rebuild as you modify the tailwind source or html templates.<br/>
`uv run --env-file .env manage.py runserver 127.0.0.1:8000` to run the server locally on port 800<br/>

# Formatting and Linting
`uv run black .` <br/>
`uv run --env-file .env pylint diagnostics config scripts manage.py` - running with your .env pointed at dev is fine, but it needs to load a valid .env to initialize django.<br/>
