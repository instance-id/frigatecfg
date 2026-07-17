"""Flask application factory and configuration."""

from __future__ import annotations

import os
from pathlib import Path

import sass
from flask import Flask

from . import models
from .credential_loader import load_env_credentials


def compile_sass(app: Flask) -> None:
    """Compile SASS files to CSS at startup."""
    sass_dir = Path(app.static_folder) / "sass"
    css_dir = Path(app.static_folder) / "css"
    css_dir.mkdir(parents=True, exist_ok=True)

    if not sass_dir.exists():
        return

    sass_files = list(sass_dir.glob("*.sass"))
    for sass_file in sass_files:
        if sass_file.name.startswith("_"):
            continue
        css_file = css_dir / sass_file.with_suffix(".css").name
        try:
            css_content = sass.compile(
                filename=str(sass_file),
                output_style="compressed" if not app.debug else "expanded",
                include_paths=[str(sass_dir)],
            )
            css_file.write_text(css_content)
        except Exception as e:
            app.logger.warning(f"SASS compile error for {sass_file.name}: {e}")


def create_app() -> Flask:
    app = Flask(
        __name__,
        template_folder=str(Path(__file__).parent / "templates"),
        static_folder=str(Path(__file__).parent.parent.parent / "static"),
    )
    app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "frigatecfg-dev-key")

    # Init database
    models.init_db()

    # Load credentials from environment variables
    load_env_credentials()

    # Compile SASS
    compile_sass(app)

    # Register template filters
    @app.template_filter("field_value")
    def field_value(config, field_path):
        from .config_manager import deep_get
        return deep_get(config, field_path)

    @app.template_filter("fields_tojson")
    def fields_tojson(fields):
        import json
        result = []
        for f in fields:
            result.append({
                "name": f.name,
                "label": f.label,
                "type": f.type.value,
                "options": f.options,
                "required": f.required,
                "default": f.default,
                "description": f.description,
            })
        return json.dumps(result)

    # Register blueprints
    from .routes.main import bp as main_bp
    from .routes.cameras import bp as cameras_bp
    from .routes.settings import bp as settings_bp
    from .routes.actions import bp as actions_bp
    from .routes.discovery import bp as discovery_bp
    from .routes.credentials import bp as credentials_bp

    app.register_blueprint(main_bp)
    app.register_blueprint(cameras_bp, url_prefix="/cameras")
    app.register_blueprint(settings_bp, url_prefix="/settings")
    app.register_blueprint(actions_bp, url_prefix="/actions")
    app.register_blueprint(discovery_bp, url_prefix="/discovery")
    app.register_blueprint(credentials_bp, url_prefix="/credentials")

    return app


app = create_app()


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080, debug=True)
