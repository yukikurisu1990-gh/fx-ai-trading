"""app_settings phase_mode + runtime_environment seed (M18 / Ob-PANEL-FALLBACK-1)

Revision ID: 0011_app_settings_phase_mode_seed
Revises: 0010_view_aliases
Create Date: 2026-04-19

Adds two operational-context keys to app_settings:
  - phase_mode       : current development phase (e.g. "phase6")
  - runtime_environment : deployment environment key (renamed from "environment"
                          to avoid collision with Common Keys D1 §3.1 row attribute)

Naming decision (IP2-Q6): `runtime_environment` is used instead of `environment`
to prevent shadowing the D1 Common Keys `environment` row attribute.

introduced_in_version = "0.0.2" separates these rows from the 0.0.1 seed so
downgrade can remove precisely what this revision added.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0011_app_settings_phase_mode_seed"
down_revision: str | None = "0010_view_aliases"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_INTRODUCED_IN = "0.0.2"

# (name, value, type, description)
_NEW_VALUES: list[tuple[str, str, str, str]] = [
    (
        "phase_mode",
        "phase6",
        "string",
        "Current development phase for dashboard display (e.g. phase6, phase7).",
    ),
    (
        "runtime_environment",
        "demo",
        "string",
        "Deployment env: demo|live. Avoids Common Keys 'environment' collision (IP2-Q6).",
    ),
]

_APP_SETTINGS_TABLE = sa.table(
    "app_settings",
    sa.column("name", sa.Text),
    sa.column("value", sa.Text),
    sa.column("type", sa.Text),
    sa.column("introduced_in_version", sa.Text),
    sa.column("description", sa.Text),
)


def upgrade() -> None:
    op.bulk_insert(
        _APP_SETTINGS_TABLE,
        [
            {
                "name": name,
                "value": value,
                "type": type_,
                "introduced_in_version": _INTRODUCED_IN,
                "description": description,
            }
            for name, value, type_, description in _NEW_VALUES
        ],
    )


def downgrade() -> None:
    op.execute(
        sa.text("DELETE FROM app_settings WHERE introduced_in_version = :v").bindparams(
            v=_INTRODUCED_IN
        )
    )
