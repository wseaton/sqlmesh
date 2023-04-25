from __future__ import annotations

import logging
import sys

import click

from sqlmesh.integrations.github.cicd.controller import (
    GithubCommitStatus,
    GithubController,
)
from sqlmesh.utils.errors import MissingARequiredApprover, PlanError

logger = logging.getLogger(__name__)


@click.group()
@click.pass_context
def github(ctx: click.Context) -> None:
    """Dumps information about the GitHub integration."""
    ctx.obj["github"] = GithubController(ctx.obj["context"])


def _check_required_approvers(controller: GithubController) -> None:
    controller.update_required_approval_merge_commit_status(status=GithubCommitStatus.PENDING)
    if not controller.has_required_approval:
        controller.update_required_approval_merge_commit_status(status=GithubCommitStatus.FAILURE)
        raise MissingARequiredApprover()
    controller.update_required_approval_merge_commit_status(status=GithubCommitStatus.SUCCESS)


@github.command()
@click.pass_context
def check_required_approvers(ctx: click.Context) -> None:
    """Dumps information about the GitHub integration."""
    _check_required_approvers(ctx.obj["github"])


def _update_pr_environment(controller: GithubController) -> None:
    controller.update_pr_environment_merge_commit_status(status=GithubCommitStatus.PENDING)
    try:
        controller.update_pr_environment()
        controller.update_pr_environment_merge_commit_status(status=GithubCommitStatus.SUCCESS)
    except PlanError as e:
        controller.post_pr_has_uncategorized_changes()
        controller.update_pr_environment_merge_commit_status(status=GithubCommitStatus.FAILURE)
        logger.warning(e)
        sys.exit(1)


@github.command()
@click.pass_context
def update_pr_environment(ctx: click.Context) -> None:
    """Creates or updates the PR environments"""
    _update_pr_environment(ctx.obj["github"])


def _deploy_production(controller: GithubController) -> None:
    controller.update_prod_environment_merge_commit_status(status=GithubCommitStatus.PENDING)
    try:
        controller.deploy_to_prod()
        controller.update_prod_environment_merge_commit_status(status=GithubCommitStatus.SUCCESS)
    except PlanError as e:
        controller.post_pr_has_uncategorized_changes()
        controller.update_prod_environment_merge_commit_status(status=GithubCommitStatus.FAILURE)
        logger.warning(e)
        sys.exit(1)


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
    controller.update_required_approval_merge_commit_status(status=GithubCommitStatus.PENDING)
    controller.update_pr_environment_merge_commit_status(status=GithubCommitStatus.PENDING)
    controller.update_prod_environment_merge_commit_status(status=GithubCommitStatus.PENDING)
    _check_required_approvers(controller)
    _update_pr_environment(controller)
    _deploy_production(controller)
