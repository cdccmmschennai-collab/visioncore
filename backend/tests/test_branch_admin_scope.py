"""Tests for the branch-admin team-scoping helper (app/core/deps.py).

No database is exercised — team_scope() only reads .role/.team off an
in-memory User instance, matching the rest of this suite's pure-unit style
(see test_sync_client.py's docstring). The DB-backed authorization paths
(admin.py's scoped queries, _load_batch, list_history) are exercised
end-to-end by the manual test plan in this feature's implementation report.
"""
from app.core.deps import team_scope
from app.models import Team, User, UserRole


def _user(role: UserRole, team: Team = Team.CHENNAI) -> User:
    return User(username="x", hashed_password="x", role=role, team=team)


def test_overall_admin_scope_is_unrestricted():
    assert team_scope(_user(UserRole.ADMIN, Team.HYDERABAD)) is None


def test_branch_admin_scope_is_their_own_team():
    assert team_scope(_user(UserRole.BRANCH_ADMIN, Team.HYDERABAD)) == Team.HYDERABAD
    assert team_scope(_user(UserRole.BRANCH_ADMIN, Team.QATAR)) == Team.QATAR


def test_plain_user_scope_is_none_but_never_meant_to_be_used_for_team_filtering():
    # A plain USER's endpoints stay scoped to their own user_id (see
    # batches.py/history.py/tags.py), never to team_scope() — this just
    # documents that calling it on a USER returns None (same shape as
    # Overall Admin) rather than raising, so a caller can't accidentally
    # treat "None" as "definitely an admin".
    assert team_scope(_user(UserRole.USER, Team.QATAR)) is None


def test_user_role_has_exactly_three_values_admin_meaning_unchanged():
    assert {r.value for r in UserRole} == {"admin", "branch_admin", "user"}


def test_team_enum_has_exactly_three_branches():
    assert {t.value for t in Team} == {"CHENNAI", "HYDERABAD", "QATAR"}
