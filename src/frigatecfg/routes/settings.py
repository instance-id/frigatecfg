"""Settings routes: edit global config sections."""

from __future__ import annotations

from flask import Blueprint, render_template, request

from .. import models
from ..config_manager import load_config, save_config, deep_clone, deep_get, deep_set, get_cameras
from ..config_schema import SECTION_MAP, ALL_SECTIONS

bp = Blueprint("settings", __name__)


@bp.route("/<section_name>")
def edit_section(section_name):
    """HTMX partial: edit a global config section."""
    section = SECTION_MAP.get(section_name)
    if not section:
        return render_template("partials/error.html", message=f"Unknown section: {section_name}")

    config = load_config()
    current_value = config.get(section_name, {})
    camera_names = list(get_cameras(config).keys())

    return render_template(
        "partials/section_editor.html",
        section=section,
        current_value=current_value,
        config=config,
        camera_names=camera_names,
    )


@bp.route("/<section_name>", methods=["POST"])
def save_section(section_name):
    section = SECTION_MAP.get(section_name)
    if not section:
        return render_template("partials/error.html", message=f"Unknown section: {section_name}")

    config = load_config()
    old_value = deep_clone(config.get(section_name, {}))

    # Parse form data into config dict
    new_value = parse_section_from_form(section, request.form, section_name, current_value=old_value)

    config[section_name] = new_value
    old_config = deep_clone(config)
    save_config(config, description=f"Updated {section_name}")
    models.push_undo("update_section", section_name, None, old_value, new_value)

    return render_template(
        "partials/section_editor.html",
        section=section,
        current_value=new_value,
        config=config,
        saved=True,
        camera_names=list(get_cameras(config).keys()),
    )


def parse_section_from_form(section, form, prefix="", current_value=None) -> dict:
    """Parse form data into a config dict based on section schema."""
    result = {}

    if section.is_dict_collection:
        # Dict collection: keys are user-defined names
        i = 0
        while True:
            key = form.get(f"{prefix}_key_{i}")
            if key is None:
                break
            if key.strip():
                item = {}
                for field in section.item_fields:
                    val = form.get(f"{prefix}_{i}_{field.name}")
                    if val is not None:
                        item[field.name] = _convert_value(val, field)
                result[key.strip()] = item
            i += 1
        return result

    for field in section.fields:
        _parse_field(form, field, result, prefix)

    return result


def _parse_field(form, field, result, prefix=""):
    field_key = f"{prefix}_{field.name}" if prefix else field.name

    from ..config_schema import FieldType

    if field.type == FieldType.SECTION:
        sub = {}
        for sub_field in field.fields:
            _parse_field(form, sub_field, sub, field_key)
        if sub:
            result[field.name] = sub
        return

    if field.type == FieldType.DICT:
        # Dict with user-defined keys
        i = 0
        while True:
            key = form.get(f"{field_key}_key_{i}")
            if key is None:
                break
            if key.strip():
                if field.fields:
                    sub = {}
                    for sub_field in field.fields:
                        sub_val = form.get(f"{field_key}_{i}_{sub_field.name}")
                        if sub_val is not None:
                            sub[sub_field.name] = _convert_value(sub_val, sub_field)
                    result.setdefault(field.name, {})[key.strip()] = sub
                else:
                    val = form.get(f"{field_key}_{i}_value")
                    if val is not None:
                        # If original value was a list, split comma-separated input
                        orig = current_value.get(field.name, {}).get(key.strip()) if current_value else None
                        if isinstance(orig, list):
                            result.setdefault(field.name, {})[key.strip()] = [v.strip() for v in val.split(",") if v.strip()]
                        else:
                            result.setdefault(field.name, {})[key.strip()] = val
            i += 1
        return

    if field.type == FieldType.LIST:
        items = form.getlist(f"{field_key}[]")
        if not items:
            items = form.getlist(field_key)
        if items:
            result[field.name] = items
        return

    val = form.get(field_key)
    if val is not None and val != "":
        result[field.name] = _convert_value(val, field)


def _convert_value(val, field):
    from ..config_schema import FieldType

    if field.type in (FieldType.INTEGER,):
        try:
            return int(val)
        except ValueError:
            return val
    if field.type in (FieldType.FLOAT,):
        try:
            return float(val)
        except ValueError:
            return val
    if field.type == FieldType.BOOLEAN:
        return val in ("on", "true", "True", "1")
    return val
