"""`gs gmail` — the Gmail command group (tail, send, read, mark, rm, mv, label, ...)."""

import click

from .tail import tail
from .repl import repl
from .read import read
from .mark import mark
from .send import send
from .rm import rm
from .mv import mv
from .label import label
from .profile import profile


@click.group()
def gmail():
    """Manage and monitor Gmail."""


for _cmd in (tail, repl, read, mark, send, rm, mv, label, profile):
    gmail.add_command(_cmd)
