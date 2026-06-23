# Flask-Migrate

Flask-Migrate is configured in `app.py` via `migrate.init_app(app, db)`.

For a real production database, initialize migrations with:

```bash
flask --app app db init
flask --app app db migrate -m "initial schema"
flask --app app db upgrade
```

The local SQLite prototype also runs a small safe upgrade helper for new demo columns.
