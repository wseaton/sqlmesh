from __future__ import annotations

import typing as t

import click

from sqlmesh.cli import error_handler
from sqlmesh.cli import options as opt
from sqlmesh.core.context import Context
from sqlmesh.integrations.github.cicd.command import github


@click.group(no_args_is_help=True)
@opt.paths
@opt.config
@click.pass_context
@error_handler
def bot(
    ctx: click.Context,
    paths: t.List[str],
    config: t.Optional[str] = None,
) -> None:
    """SQLMesh CI/CD Bot."""
    print("In sqlmesh bot")
    ctx.obj = {
        "context": Context(
            paths=paths,
            config=config,
        )
    }
    print("finished slqmesh bot")


bot.add_command(github)


if __name__ == "__main__":
    print("I'm in main")
    bot()
