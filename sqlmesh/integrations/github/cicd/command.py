from __future__ import annotations

import logging

import click

from sqlmesh.integrations.github.cicd.controller import (
    GithubCommitConclusion,
    GithubCommitStatus,
    GithubController,
)
from sqlmesh.utils.errors import PlanError

logger = logging.getLogger(__name__)


@click.group(no_args_is_help=True)
@click.option(
    "-t",
    "--token",
    type=str,
    help="The Github Token to be used. Pass in `${{ secrets.GITHUB_TOKEN }}` if you want to use the one created by Github actions",
)
@click.pass_context
def github(ctx: click.Context, token: str) -> None:
    """Github Action CI/CD Bot"""
    ctx.obj["github"] = GithubController(
        paths=ctx.obj["paths"],
        token=token,
        config=ctx.obj["config"],
    )


def _check_required_approvers(controller: GithubController) -> bool:
    controller.update_required_approval_check(status=GithubCommitStatus.IN_PROGRESS)
    if controller.has_required_approval:
        controller.update_required_approval_check(
            status=GithubCommitStatus.COMPLETED, conclusion=GithubCommitConclusion.SUCCESS
        )
        return True
    controller.update_required_approval_check(
        status=GithubCommitStatus.COMPLETED, conclusion=GithubCommitConclusion.NEUTRAL
    )
    return False


@github.command()
@click.pass_context
def check_required_approvers(ctx: click.Context) -> None:
    """Checks if a required approver has provided approval on the PR."""
    _check_required_approvers(ctx.obj["github"])


def _update_pr_environment(controller: GithubController) -> bool:
    controller.update_pr_environment_check(status=GithubCommitStatus.IN_PROGRESS)
    try:
        controller.update_pr_environment()
        controller.update_pr_environment_check(
            status=GithubCommitStatus.COMPLETED, conclusion=GithubCommitConclusion.SUCCESS
        )
        return True
    except PlanError:
        # controller.post_pr_has_uncategorized_changes()
        controller.update_pr_environment_check(
            status=GithubCommitStatus.COMPLETED, conclusion=GithubCommitConclusion.ACTION_REQUIRED
        )
        return False


@github.command()
@click.pass_context
def update_pr_environment(ctx: click.Context) -> None:
    """Creates or updates the PR environments"""
    _update_pr_environment(ctx.obj["github"])


def _deploy_production(controller: GithubController) -> bool:
    controller.update_prod_environment_check(status=GithubCommitStatus.IN_PROGRESS)
    try:
        controller.deploy_to_prod()
        controller.update_prod_environment_check(
            status=GithubCommitStatus.COMPLETED, conclusion=GithubCommitConclusion.SUCCESS
        )
        return True
    except PlanError:
        # controller.post_pr_has_uncategorized_changes()
        controller.update_prod_environment_check(
            status=GithubCommitStatus.COMPLETED, conclusion=GithubCommitConclusion.ACTION_REQUIRED
        )
        return False


@github.command()
@click.pass_context
def deploy_production(ctx: click.Context) -> None:
    """Deploys the production environment"""
    _deploy_production(ctx.obj["github"])


@github.command()
@click.pass_context
def run_all(ctx: click.Context) -> None:
    """Runs all the commands in the correct order."""
    controller = ctx.obj["github"]
    controller.update_required_approval_check(status=GithubCommitStatus.QUEUED)
    controller.update_pr_environment_check(status=GithubCommitStatus.QUEUED)
    controller.update_prod_environment_check(status=GithubCommitStatus.QUEUED)
    try:
        if not _update_pr_environment(controller):
            controller.update_pr_environment_check(
                status=GithubCommitStatus.COMPLETED, conclusion=GithubCommitConclusion.SKIPPED
            )
            controller.update_prod_environment_check(
                status=GithubCommitStatus.COMPLETED, conclusion=GithubCommitConclusion.SKIPPED
            )
            return
    except Exception as e:
        controller.update_pr_environment_check(
            status=GithubCommitStatus.COMPLETED, conclusion=GithubCommitConclusion.SKIPPED
        )
        controller.update_prod_environment_check(
            status=GithubCommitStatus.COMPLETED, conclusion=GithubCommitConclusion.SKIPPED
        )
        raise e
    try:
        if not _check_required_approvers(controller):
            controller.update_prod_environment_check(
                status=GithubCommitStatus.COMPLETED, conclusion=GithubCommitConclusion.SKIPPED
            )
            return
    except Exception as e:
        controller.update_prod_environment_check(
            status=GithubCommitStatus.COMPLETED, conclusion=GithubCommitConclusion.SKIPPED
        )
        raise e
    _deploy_production(controller)
