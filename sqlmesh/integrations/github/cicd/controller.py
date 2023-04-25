from __future__ import annotations

import json
import logging
import os
import pathlib
import typing as t
from enum import Enum

from sqlmesh.core import constants as c
from sqlmesh.core.context import Context
from sqlmesh.core.environment import Environment
from sqlmesh.core.model import parse_model_name
from sqlmesh.core.notification_target import NotificationStatus
from sqlmesh.core.user import User
from sqlmesh.integrations.github.shared import PullRequestInfo, add_comment_to_pr
from sqlmesh.utils.errors import CICDBotError

if t.TYPE_CHECKING:
    from github import Github
    from github.PullRequest import PullRequest
    from github.PullRequestReview import PullRequestReview
    from github.Repository import Repository

logger = logging.getLogger(__name__)


class GithubCommitStatus(str, Enum):
    PENDING = "pending"
    SUCCESS = "success"
    FAILURE = "failure"
    ERROR = "error"


class GithubEvent:
    def __init__(self, payload: t.Dict[str, t.Any]) -> None:
        self.payload = payload
        self._pull_request_info: t.Optional[PullRequestInfo] = None

    @classmethod
    def from_path(cls, path: t.Union[str, pathlib.Path]) -> GithubEvent:
        with open(path) as f:
            return cls(payload=json.load(f))

    @classmethod
    def from_env(cls) -> GithubEvent:
        return cls.from_path(GithubEnvironmentConfig.GITHUB_EVENT_PATH)

    @property
    def is_review(self) -> bool:
        return bool(self.payload.get("review"))

    @property
    def is_comment(self) -> bool:
        return bool(self.payload.get("comment"))

    @property
    def is_pull_request(self) -> bool:
        return bool(self.payload.get("pull_request"))

    @property
    def pull_request_url(self) -> str:
        if self.is_review:
            return self.payload["review"]["pull_request_url"]
        if self.is_comment:
            return self.payload["issue"]["pull_request"]["url"]
        if self.is_pull_request:
            return self.payload["pull_request"]["_links"]["self"]["href"]
        raise CICDBotError("Unable to determine pull request url")

    @property
    def pull_request_info(self) -> PullRequestInfo:
        if not self._pull_request_info:
            self._pull_request_info = PullRequestInfo.create_from_pull_request_url(
                self.pull_request_url
            )
        return self._pull_request_info


class GithubEnvironmentConfig:
    GITHUB_EVENT_PATH = os.environ["GITHUB_EVENT_PATH"]
    GITHUB_API_URL = os.environ["GITHUB_API_URL"]


class GithubController:
    def __init__(
        self, context: Context, token: str, event: GithubEvent = GithubEvent.from_env()
    ) -> None:
        self.context = context
        self.token = token
        self.event = event
        self.__client: t.Optional[Github] = None
        self.__repo: t.Optional[Repository] = None
        self.__pull_request: t.Optional[PullRequest] = None
        self.__reviews: t.Optional[t.Iterable[PullRequestReview]] = None
        self.__approvers: t.Optional[t.Set[str]] = None

    @property
    def _client(self) -> Github:
        if not self.__client:
            self.__client = Github(
                base_url=GithubEnvironmentConfig.GITHUB_API_URL,
                login_or_token=self.token,
            )
        return self.__client

    @property
    def _repo(self) -> Repository:
        if not self.__repo:
            self.__repo = self._client.get_repo(
                self.event.pull_request_info.full_repo_path, lazy=True
            )
        return self.__repo

    @property
    def _pull_request(self) -> PullRequest:
        if not self.__pull_request:
            self.__pull_request = self._repo.get_pull(self.event.pull_request_info.pr_number)
        return self.__pull_request

    @property
    def _reviews(self) -> t.Iterable[PullRequestReview]:
        if not self.__reviews:
            self.__reviews = self._pull_request.get_reviews()
        return self.__reviews

    @property
    def _approvers(self) -> t.Set[str]:
        if not self.__approvers:
            # TODO: The python module says that user names can be None and this is not currently handled
            self.__approvers = {
                review.user.name or "UNKNOWN"
                for review in self._reviews
                if review.state.lower() == "approved"
            }
        return self.__approvers

    @property
    def _required_approvers(self) -> t.Set[User]:
        return {user for user in self.context.config.users if user.is_required_approver}

    @property
    def pr_environment_name(self) -> str:
        return Environment.normalize_name(
            "_".join(
                [
                    self.event.pull_request_info.repo,
                    str(self.event.pull_request_info.pr_number),
                ]
            )
        )

    @property
    def has_required_approval(self) -> bool:
        """
        Check if the PR has a required approver.

        TODO: Allow defining requiring some number, or all, required approvers.
        """
        if len(self._required_approvers) == 0:
            return True
        if len(self._approvers) == 0:
            return False
        return bool(
            [
                approver
                for approver in self._approvers
                if approver in {x.github_username for x in self._required_approvers}
            ]
        )

    def post_notification_to_pr(
        self, notification_status: NotificationStatus, comment: str
    ) -> None:
        """
        Comment on the pull request with the provided comment. It checks if the bot has already commented on the PR
        and if so then it updates the comment instead of creating a new one.
        """
        bot_users = [user for user in self.context.config.users if user.is_bot]
        user_to_append_to = bot_users[0] if bot_users else None
        if user_to_append_to:
            logger.debug(f"Found user to append to: {user_to_append_to.github_username}")
        else:
            logger.debug("No user to append to found")
        add_comment_to_pr(
            repo=self._repo,
            pull_request_info=self.event.pull_request_info,
            notification_status=notification_status,
            msg=comment,
            user_to_append_to=user_to_append_to,
        )

    def post_pr_has_uncategorized_changes(self) -> None:
        """
        Post a comment on the PR that there are uncategorized changes.
        """
        self.post_notification_to_pr(
            notification_status=NotificationStatus.FAILURE,
            comment="The plan for this PR is not up to date. Please run `sqlmesh plan` and commit the changes.",
        )

    def update_pr_environment(self) -> None:
        """
        Creates a PR environment from the logic present in the PR. If the PR contains changes that are
        uncategorized, then an error will be raised.
        """
        self.context.plan(
            environment=self.pr_environment_name,
            skip_backfill=True,
            auto_apply=True,
            no_prompts=True,
        )

    def deploy_to_prod(self) -> None:
        """
        Attempts to deploy a plan to prod. If the plan is not up-to-date or has gaps then it will raise.
        """
        self.context.plan(c.PROD, auto_apply=True, no_gaps=True, no_prompts=True)

    def delete_pr_environment(self) -> None:
        """
        Deletes all the schemas for a given environment by checking all the schemas used by models.
        """
        schemas = {parse_model_name(model.name)[1] for model in self.context.models.values()}
        for schema in schemas:
            assert schema
            self.context.engine_adapter.drop_schema(
                schema_name="__".join([schema, self.pr_environment_name]),
                ignore_if_not_exists=True,
                cascade=True,
            )
        return

    def _update_merge_commit_status(self, name: str, status: GithubCommitStatus) -> None:
        """
        Updates the status of the merge commit.
        """
        self._repo.get_commit(self._pull_request.merge_commit_sha).create_status(
            state=str(status), context=name
        )

    def update_required_approval_merge_commit_status(self, status: GithubCommitStatus) -> None:
        """
        Updates the status of the merge commit for the required approval.
        """
        self._update_merge_commit_status(name="Has Required Approval", status=status)

    def update_pr_environment_merge_commit_status(self, status: GithubCommitStatus) -> None:
        """
        Updates the status of the merge commit for the PR environment.
        """
        self._update_merge_commit_status(name="PR Environment Synced", status=status)

    def update_prod_environment_merge_commit_status(self, status: GithubCommitStatus) -> None:
        """
        Updates the status of the merge commit for the prod environment.
        """
        self._update_merge_commit_status(name="Prod Environment Synced", status=status)

    def merge_pr(self) -> None:
        """
        Merges the PR
        """
        self._pull_request.merge()