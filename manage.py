#!/usr/bin/env python
"""Django's command-line utility for administrative tasks.
ex: docker compose exec web python manage.py prune_reports --days 180 --dry-run"""

import os
import sys


def main() -> None:
    """Run administrative tasks."""
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
    from django.core.management import (  # pylint: disable=import-outside-toplevel
        execute_from_command_line,
    )

    execute_from_command_line(sys.argv)


if __name__ == "__main__":
    main()
