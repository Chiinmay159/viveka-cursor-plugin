"""
Comprehensive test suite for MicroDecisionEngine.

Coverage:
    - All 7 rule categories
    - All 4 enforcement modes (RiskMode)
    - Retry detection edge cases and normalization
    - Performance benchmark (< 1ms per evaluation)
    - Session state tracking
    - Verdict severity ranking
"""

from __future__ import annotations

import time

import pytest

from viveka.models.core import (
    Environment,
    EnvironmentState,
    Option,
    Permissions,
    Reversibility,
    RiskMode,
    TaskContext,
    TokenBudget,
)
from viveka.micro import (
    MicroDecision,
    MicroDecisionEngine,
    SessionState,
    Verdict,
    _is_read_only_action,
    _looks_like_file_edit,
    _matches_any,
    _normalize_action,
)


# ═══════════════════════════════════════════════════════════
# 1. INVARIANTS (_check_invariants)
# ═══════════════════════════════════════════════════════════


class TestInvariants:
    """Hard invariant violations via scanner.find_invariant_violations."""

    def test_budget_exhausted_blocks(self, make_engine, make_env):
        env = make_env(budget=TokenBudget(max_tokens=100, used_tokens=100))
        engine = make_engine(env=env)
        d = engine.evaluate("edit file.py")
        assert d.verdict == Verdict.BLOCK
        assert "budget" in d.rule.lower() or "budget" in d.reason.lower()

    def test_deploy_in_production_without_permission_blocks(self, make_engine, make_env):
        env = make_env(
            environment=Environment.PRODUCTION,
            can_deploy=False,
        )
        engine = make_engine(env=env)
        d = engine.evaluate("deploy to production")
        assert d.verdict == Verdict.BLOCK
        assert "deploy" in d.reason.lower()

    def test_deploy_in_dev_permits(self, make_engine, make_env):
        env = make_env(environment=Environment.DEVELOPMENT)
        engine = make_engine(env=env)
        d = engine.evaluate("deploy to staging")
        assert d.verdict in (Verdict.PERMIT, Verdict.WARN)

    def test_force_push_on_protected_branch_blocks(self, make_engine, make_env):
        env = make_env(git_branch="main", is_protected_branch=True)
        engine = make_engine(env=env)
        d = engine.evaluate("git force push to remote")
        assert d.verdict == Verdict.BLOCK

    def test_reset_hard_on_protected_branch_blocks(self, make_engine, make_env):
        env = make_env(git_branch="main", is_protected_branch=True)
        engine = make_engine(env=env)
        d = engine.evaluate("git reset --hard HEAD~3")
        assert d.verdict == Verdict.BLOCK

    def test_blocked_path_blocks(self, make_engine, make_env):
        env = make_env(blocked_paths=["/etc/passwd"])
        engine = make_engine(env=env)
        d = engine.evaluate("edit /etc/passwd")
        assert d.verdict == Verdict.BLOCK

    def test_blocked_tool_blocks(self, make_engine, make_env):
        env = make_env(blocked_tools=["kubectl"])
        engine = make_engine(env=env)
        d = engine.evaluate("kubectl delete pods")
        assert d.verdict == Verdict.BLOCK

    def test_clean_action_permits(self, standard_engine):
        d = standard_engine.evaluate("edit utils.py")
        assert d.verdict == Verdict.PERMIT

    def test_production_git_push_without_modify_git_blocks(self, make_engine, make_env):
        env = make_env(
            environment=Environment.PRODUCTION,
            can_modify_git=False,
        )
        engine = make_engine(env=env)
        d = engine.evaluate("git push origin main")
        assert d.verdict == Verdict.BLOCK


# ═══════════════════════════════════════════════════════════
# 2. PROTECTED RESOURCES (_check_protected_resources)
# ═══════════════════════════════════════════════════════════


class TestProtectedResources:
    """Sensitive files and secrets detection."""

    @pytest.mark.parametrize("keyword", [
        "secret", "credential", "api_key", "password",
        ".env", "token", "private_key",
    ])
    def test_secret_keywords_warn_without_permission(self, keyword, make_engine, make_env):
        env = make_env(can_access_secrets=False)
        engine = make_engine(env=env)
        d = engine.evaluate(f"read the {keyword} file")
        assert d.verdict == Verdict.WARN
        assert "secret" in d.reason.lower() or "credential" in d.reason.lower()

    @pytest.mark.parametrize("keyword", ["secret", "api_key", ".env"])
    def test_secret_keywords_permit_with_permission(self, keyword, make_engine, make_env):
        env = make_env(can_access_secrets=True)
        engine = make_engine(env=env)
        d = engine.evaluate(f"read the {keyword} file")
        assert d.verdict == Verdict.PERMIT

    def test_non_secret_action_permits(self, standard_engine):
        d = standard_engine.evaluate("edit readme.md")
        assert d.verdict == Verdict.PERMIT

    def test_case_insensitive_secret_detection(self, make_engine, make_env):
        env = make_env(can_access_secrets=False)
        engine = make_engine(env=env)
        d = engine.evaluate("read API_KEY from vault")
        assert d.verdict == Verdict.WARN


# ═══════════════════════════════════════════════════════════
# 3. RETRY LOOPS (_check_retry_loops)
# ═══════════════════════════════════════════════════════════


class TestRetryLoops:
    """Blind retry pattern detection."""

    def test_first_attempt_permits(self, standard_engine):
        d = standard_engine.evaluate("edit auth.py")
        assert d.verdict == Verdict.PERMIT

    def test_standard_mode_blocks_after_max_retries(self, standard_engine):
        for _ in range(3):
            standard_engine.evaluate("edit auth.py")
        d = standard_engine.evaluate("edit auth.py")
        assert d.verdict == Verdict.BLOCK
        assert "retry" in d.reason.lower()

    def test_permissive_mode_allows_more_retries(self, permissive_engine):
        for _ in range(5):
            permissive_engine.evaluate("edit auth.py")
        d = permissive_engine.evaluate("edit auth.py")
        assert d.verdict == Verdict.BLOCK

    def test_restricted_mode_blocks_on_second_retry(self, restricted_engine):
        restricted_engine.evaluate("edit auth.py")
        d = restricted_engine.evaluate("edit auth.py")
        assert d.verdict == Verdict.BLOCK

    def test_guarded_mode_blocks_after_two_retries(self, guarded_engine):
        guarded_engine.evaluate("edit auth.py")
        guarded_engine.evaluate("edit auth.py")
        d = guarded_engine.evaluate("edit auth.py")
        assert d.verdict == Verdict.BLOCK

    def test_retry_warning_before_block(self, standard_engine):
        """STANDARD max_retries=3. Warning at count > max_retries//2 (i.e. >1)."""
        standard_engine.evaluate("edit auth.py")
        d = standard_engine.evaluate("edit auth.py")
        assert d.verdict == Verdict.WARN
        assert "retry" in d.reason.lower() or "repeated" in d.reason.lower()

    def test_different_actions_dont_trigger_retry(self, standard_engine):
        standard_engine.evaluate("edit auth.py")
        standard_engine.evaluate("edit views.py")
        standard_engine.evaluate("edit models.py")
        d = standard_engine.evaluate("edit urls.py")
        assert d.verdict == Verdict.PERMIT

    def test_read_operations_exempt_from_retry(self, standard_engine):
        for _ in range(10):
            d = standard_engine.evaluate("read_file auth.py")
        assert d.verdict == Verdict.PERMIT

    def test_test_commands_exempt_from_retry(self, standard_engine):
        for _ in range(10):
            d = standard_engine.evaluate("run_tests pytest tests/")
        assert d.verdict == Verdict.PERMIT

    def test_pytest_exempt_from_retry(self, standard_engine):
        for _ in range(10):
            d = standard_engine.evaluate("pytest tests/test_auth.py")
        assert d.verdict == Verdict.PERMIT


# ═══════════════════════════════════════════════════════════
# 4. SCOPE DRIFT (_check_scope_drift)
# ═══════════════════════════════════════════════════════════


class TestScopeDrift:
    """Scope creep and tool thrashing detection."""

    def test_many_file_edits_warn(self, make_engine):
        engine = make_engine(risk_mode=RiskMode.STANDARD)
        for i in range(16):
            engine.record_file_modified(f"file_{i}.py")
        d = engine.evaluate("edit file_16.py")
        assert d.verdict == Verdict.WARN
        assert "scope" in d.reason.lower() or "files" in d.reason.lower()

    def test_file_count_within_limit_permits(self, make_engine):
        engine = make_engine(risk_mode=RiskMode.STANDARD)
        for i in range(10):
            engine.record_file_modified(f"file_{i}.py")
        d = engine.evaluate("edit something.py")
        assert d.verdict == Verdict.PERMIT

    def test_restricted_mode_lower_file_limit(self, make_engine):
        engine = make_engine(risk_mode=RiskMode.RESTRICTED)
        for i in range(4):
            engine.record_file_modified(f"file_{i}.py")
        d = engine.evaluate("edit file_4.py")
        assert d.verdict == Verdict.WARN

    def test_tool_thrashing_warns(self, make_engine):
        engine = make_engine(risk_mode=RiskMode.STANDARD)
        for i in range(11):
            engine.record_tool_used(f"tool_{i}")
        d = engine.evaluate("run something")
        assert d.verdict == Verdict.WARN
        assert "tool" in d.reason.lower()

    def test_tool_diversity_within_limit_permits(self, make_engine):
        engine = make_engine(risk_mode=RiskMode.STANDARD)
        for i in range(8):
            engine.record_tool_used(f"tool_{i}")
        d = engine.evaluate("run something")
        assert d.verdict == Verdict.PERMIT

    def test_scope_drift_not_triggered_on_non_edit_action(self, make_engine):
        """Scope drift file warning only fires when action looks like a file edit."""
        engine = make_engine(risk_mode=RiskMode.STANDARD)
        for i in range(20):
            engine.record_file_modified(f"file_{i}.py")
        d = engine.evaluate("run pytest")
        assert d.verdict == Verdict.PERMIT


# ═══════════════════════════════════════════════════════════
# 5. DESTRUCTIVE ACTIONS (_check_destructive_actions)
# ═══════════════════════════════════════════════════════════


class TestDestructiveActions:
    """Destructive action detection across enforcement modes."""

    @pytest.mark.parametrize("action", [
        "delete the user table",
        "drop table users",
        "rm -rf /tmp/build",
        "rm -r old_dir",
        "force push to main",
        "git push --force origin",
        "git push -f origin",
        "git reset --hard HEAD~5",
        "git clean -fd",
        "destroy the staging env",
        "purge cache entries",
        "truncate logs table",
    ])
    def test_destructive_actions_blocked_in_guarded(self, action, make_engine):
        engine = make_engine(risk_mode=RiskMode.GUARDED)
        d = engine.evaluate(action)
        assert d.verdict == Verdict.BLOCK
        assert "destructive" in d.reason.lower()

    @pytest.mark.parametrize("action", [
        "delete the user table",
        "rm -rf /tmp/build",
        "git push --force origin",
    ])
    def test_destructive_actions_blocked_in_restricted(self, action, make_engine):
        engine = make_engine(risk_mode=RiskMode.RESTRICTED)
        d = engine.evaluate(action)
        assert d.verdict == Verdict.BLOCK

    @pytest.mark.parametrize("action", [
        "delete temporary files",
        "rm -rf build/",
    ])
    def test_destructive_actions_warn_in_standard_high_reversibility(self, action, make_engine, make_ctx):
        ctx = make_ctx(reversibility=Reversibility.HIGH)
        engine = make_engine(risk_mode=RiskMode.STANDARD, ctx=ctx)
        d = engine.evaluate(action)
        assert d.verdict == Verdict.WARN

    @pytest.mark.parametrize("action", [
        "delete production database",
        "drop database prod",
    ])
    def test_destructive_actions_escalate_low_reversibility(self, action, make_engine, make_ctx):
        ctx = make_ctx(reversibility=Reversibility.LOW)
        engine = make_engine(risk_mode=RiskMode.STANDARD, ctx=ctx)
        d = engine.evaluate(action)
        assert d.verdict == Verdict.ESCALATE

    def test_destructive_action_escalate_irreversible(self, make_engine, make_ctx):
        ctx = make_ctx(reversibility=Reversibility.IRREVERSIBLE)
        engine = make_engine(risk_mode=RiskMode.STANDARD, ctx=ctx)
        d = engine.evaluate("delete all user data")
        assert d.verdict == Verdict.ESCALATE

    def test_destructive_actions_warn_in_permissive(self, make_engine, make_ctx):
        ctx = make_ctx(reversibility=Reversibility.HIGH)
        engine = make_engine(risk_mode=RiskMode.PERMISSIVE, ctx=ctx)
        d = engine.evaluate("rm -rf build/")
        assert d.verdict == Verdict.WARN

    def test_non_destructive_action_permits(self, standard_engine):
        d = standard_engine.evaluate("read file.py")
        assert d.verdict == Verdict.PERMIT


# ═══════════════════════════════════════════════════════════
# 6. TOKEN BUDGET (_check_token_budget)
# ═══════════════════════════════════════════════════════════


class TestTokenBudget:
    """Token budget enforcement."""

    def test_no_budget_permits(self, standard_engine):
        d = standard_engine.evaluate("edit file.py")
        assert d.verdict == Verdict.PERMIT

    def test_budget_exhausted_blocks(self, make_engine, budget_env_exhausted):
        engine = make_engine(env=budget_env_exhausted)
        d = engine.evaluate("edit file.py")
        assert d.verdict == Verdict.BLOCK

    def test_budget_near_limit_warns(self, make_engine, budget_env_near_limit):
        engine = make_engine(env=budget_env_near_limit)
        d = engine.evaluate("edit file.py")
        assert d.verdict == Verdict.WARN
        assert "budget" in d.reason.lower()

    def test_budget_under_threshold_permits(self, make_engine, make_env):
        env = make_env(budget=TokenBudget(max_tokens=1000, used_tokens=500))
        engine = make_engine(env=env)
        d = engine.evaluate("edit file.py")
        assert d.verdict == Verdict.PERMIT

    def test_budget_at_exact_warn_threshold(self, make_engine, make_env):
        env = make_env(budget=TokenBudget(max_tokens=1000, used_tokens=800, warn_at=0.8))
        engine = make_engine(env=env)
        d = engine.evaluate("edit file.py")
        assert d.verdict == Verdict.WARN

    def test_budget_just_below_warn_threshold(self, make_engine, make_env):
        env = make_env(budget=TokenBudget(max_tokens=1000, used_tokens=799, warn_at=0.8))
        engine = make_engine(env=env)
        d = engine.evaluate("edit file.py")
        assert d.verdict == Verdict.PERMIT

    def test_custom_warn_threshold(self, make_engine, make_env):
        env = make_env(budget=TokenBudget(max_tokens=1000, used_tokens=600, warn_at=0.5))
        engine = make_engine(env=env)
        d = engine.evaluate("edit file.py")
        assert d.verdict == Verdict.WARN


# ═══════════════════════════════════════════════════════════
# 7. SESSION HEALTH (_check_session_health)
# ═══════════════════════════════════════════════════════════


class TestSessionHealth:
    """Overall session health monitoring."""

    def test_warning_accumulation_escalates(self, make_engine, make_env):
        env = make_env(can_access_secrets=False)
        engine = make_engine(env=env, risk_mode=RiskMode.STANDARD)
        # Use distinct actions to avoid retry detection — each triggers a
        # protected-resources WARN via a different secret keyword.
        secret_actions = [
            "check secret alpha",
            "check credential beta",
            "check api_key gamma",
            "check password delta",
            "check .env epsilon",
            "check token zeta",
            "check private_key eta",
            "check secret theta",
            "check credential iota",
        ]
        for action in secret_actions:
            engine.evaluate(action)
        d = engine.evaluate("do something normal")
        assert d.verdict == Verdict.ESCALATE
        assert "warning" in d.reason.lower()

    def test_action_limit_escalates(self, make_engine):
        engine = make_engine(risk_mode=RiskMode.RESTRICTED)
        for i in range(21):
            engine.evaluate(f"action_{i} on unique_file_{i}.py")
        d = engine.evaluate("one more action on final.py")
        assert d.verdict == Verdict.ESCALATE
        assert "action" in d.reason.lower()

    def test_undeclared_assumptions_warn(self, make_engine):
        engine = make_engine(risk_mode=RiskMode.STANDARD)
        for _ in range(6):
            engine.record_assumption("something", declared=False)
        d = engine.evaluate("edit file.py")
        assert d.verdict == Verdict.WARN
        assert "assumption" in d.reason.lower()

    def test_declared_assumptions_dont_warn(self, make_engine):
        engine = make_engine(risk_mode=RiskMode.STANDARD)
        for _ in range(10):
            engine.record_assumption("something", declared=True)
        d = engine.evaluate("edit file.py")
        assert d.verdict == Verdict.PERMIT

    def test_healthy_session_permits(self, standard_engine):
        d = standard_engine.evaluate("edit file.py")
        assert d.verdict == Verdict.PERMIT


# ═══════════════════════════════════════════════════════════
# ENFORCEMENT MODES (cross-cutting)
# ═══════════════════════════════════════════════════════════


class TestEnforcementModes:
    """Verify limits scale correctly across all 4 RiskMode values."""

    MODES_ORDERED = [
        RiskMode.PERMISSIVE,
        RiskMode.STANDARD,
        RiskMode.GUARDED,
        RiskMode.RESTRICTED,
    ]

    def test_retry_limits_decrease_with_strictness(self, make_engine):
        """More restrictive modes have fewer allowed retries."""
        limits = []
        for mode in self.MODES_ORDERED:
            engine = make_engine(risk_mode=mode)
            count = 0
            while True:
                d = engine.evaluate("edit same_file.py")
                count += 1
                if d.verdict == Verdict.BLOCK:
                    limits.append(count)
                    break
                if count > 50:
                    limits.append(count)
                    break
        assert limits == sorted(limits, reverse=True)

    def test_file_limits_decrease_with_strictness(self):
        from viveka.micro import _LIMITS
        file_limits = [_LIMITS[m]["max_files_modified"] for m in self.MODES_ORDERED]
        assert file_limits == sorted(file_limits, reverse=True)

    def test_action_limits_decrease_with_strictness(self):
        from viveka.micro import _LIMITS
        action_limits = [_LIMITS[m]["max_actions"] for m in self.MODES_ORDERED]
        assert action_limits == sorted(action_limits, reverse=True)

    def test_warning_limits_decrease_with_strictness(self):
        from viveka.micro import _LIMITS
        warn_limits = [_LIMITS[m]["max_warnings"] for m in self.MODES_ORDERED]
        assert warn_limits == sorted(warn_limits, reverse=True)

    def test_all_four_modes_have_limits(self):
        from viveka.micro import _LIMITS
        for mode in self.MODES_ORDERED:
            assert mode in _LIMITS
            limits = _LIMITS[mode]
            assert "max_retries" in limits
            assert "max_files_modified" in limits
            assert "max_unique_tools" in limits
            assert "max_warnings" in limits
            assert "max_actions" in limits
            assert "max_undeclared_assumptions" in limits


# ═══════════════════════════════════════════════════════════
# VERDICT SEVERITY & AGGREGATION
# ═══════════════════════════════════════════════════════════


class TestVerdictSeverity:
    """Worst verdict wins when multiple rules fire."""

    def test_block_overrides_warn(self, make_engine, make_env):
        """Budget exhausted (BLOCK via invariant) overrides secrets warning."""
        env = make_env(
            budget=TokenBudget(max_tokens=100, used_tokens=100),
            can_access_secrets=False,
        )
        engine = make_engine(env=env)
        d = engine.evaluate("read the secret credentials")
        assert d.verdict == Verdict.BLOCK

    def test_escalate_overrides_warn(self, make_engine, make_ctx, make_env):
        """Destructive + low reversibility (ESCALATE) overrides secrets (WARN)."""
        env = make_env(can_access_secrets=False)
        ctx = make_ctx(reversibility=Reversibility.LOW)
        engine = make_engine(env=env, ctx=ctx)
        d = engine.evaluate("delete the secret database")
        assert d.verdict == Verdict.ESCALATE

    def test_permit_with_no_issues(self, standard_engine):
        d = standard_engine.evaluate("read readme.md")
        assert d.verdict == Verdict.PERMIT
        assert d.blocked is False
        assert d.escalate is False
        assert d.permitted is True


class TestMicroDecisionProperties:
    """Verify MicroDecision convenience properties."""

    def test_permit_is_permitted(self):
        d = MicroDecision(verdict=Verdict.PERMIT, action="test")
        assert d.permitted is True
        assert d.blocked is False
        assert d.escalate is False

    def test_warn_is_permitted(self):
        d = MicroDecision(verdict=Verdict.WARN, action="test")
        assert d.permitted is True
        assert d.blocked is False
        assert d.escalate is False

    def test_block_is_not_permitted(self):
        d = MicroDecision(verdict=Verdict.BLOCK, action="test")
        assert d.permitted is False
        assert d.blocked is True
        assert d.escalate is False

    def test_escalate_is_not_permitted(self):
        d = MicroDecision(verdict=Verdict.ESCALATE, action="test")
        assert d.permitted is False
        assert d.blocked is False
        assert d.escalate is True


# ═══════════════════════════════════════════════════════════
# NORMALIZATION & UTILITY FUNCTIONS
# ═══════════════════════════════════════════════════════════


class TestNormalization:
    """_normalize_action edge cases."""

    def test_preserves_file_path_identity(self):
        assert _normalize_action("edit file1.py") != _normalize_action("edit file2.py")

    def test_normalizes_verb_digits(self):
        assert _normalize_action("retry3 file.py") == _normalize_action("retry5 file.py")

    def test_case_insensitive(self):
        assert _normalize_action("EDIT file.py") == _normalize_action("edit file.py")

    def test_single_word_normalizes_digits(self):
        assert _normalize_action("attempt3") == _normalize_action("attempt7")

    def test_whitespace_collapse(self):
        assert _normalize_action("  edit   ") == _normalize_action("edit")

    def test_empty_string(self):
        result = _normalize_action("")
        assert result == ""

    def test_verb_only_no_target(self):
        result = _normalize_action("edit")
        assert result == "edit"

    def test_numbered_files_stay_distinct(self):
        """migration_001.py and migration_002.py must not collide."""
        a = _normalize_action("edit migration_001.py")
        b = _normalize_action("edit migration_002.py")
        assert a != b

    def test_versioned_configs_stay_distinct(self):
        a = _normalize_action("edit config_v1.yaml")
        b = _normalize_action("edit config_v2.yaml")
        assert a != b


class TestMatchesAny:
    """_matches_any utility."""

    def test_match_found(self):
        assert _matches_any("delete all users", ["delete", "drop"]) is True

    def test_no_match(self):
        assert _matches_any("edit file.py", ["delete", "drop"]) is False

    def test_case_insensitive(self):
        assert _matches_any("DELETE users", ["delete"]) is True

    def test_empty_patterns(self):
        assert _matches_any("anything", []) is False

    def test_empty_text(self):
        assert _matches_any("", ["delete"]) is False


class TestIsReadOnlyAction:
    """_is_read_only_action classification."""

    @pytest.mark.parametrize("action", [
        "read_file auth.py",
        "read file config.yaml",
        "cat some_file.txt",
        "search_code pattern",
        "search code in src/",
        "grep -r pattern",
        "find . -name '*.py'",
        "ls /tmp",
        "head -n 10 file.py",
        "tail -f log.txt",
        "view output.log",
    ])
    def test_read_actions_detected(self, action):
        assert _is_read_only_action(action) is True

    @pytest.mark.parametrize("action", [
        "run_tests pytest",
        "run tests for auth",
        "pytest tests/",
        "python -m pytest tests/",
        "python3 -m pytest tests/",
        "unittest discover",
        "run_command pytest tests/",
        "run_command python -m pytest tests/",
        "run_command python3 -m pytest tests/",
    ])
    def test_test_actions_detected(self, action):
        assert _is_read_only_action(action) is True

    @pytest.mark.parametrize("action", [
        "edit file.py",
        "delete user",
        "deploy to prod",
        "create migration",
    ])
    def test_write_actions_not_read_only(self, action):
        assert _is_read_only_action(action) is False


class TestLooksLikeFileEdit:
    """_looks_like_file_edit heuristic."""

    @pytest.mark.parametrize("action", [
        "edit auth.py",
        "modify the settings",
        "write to config.yaml",
        "create file migrations/0001.py",
        "update the schema",
        "append to log",
        "replace string in file",
        "insert at line 42",
        "delete line 10",
    ])
    def test_file_edit_actions_detected(self, action):
        assert _looks_like_file_edit(action) is True

    @pytest.mark.parametrize("action", [
        "run pytest",
        "deploy app",
        "restart server",
        "git push",
    ])
    def test_non_edit_actions(self, action):
        assert _looks_like_file_edit(action) is False


# ═══════════════════════════════════════════════════════════
# SESSION STATE TRACKING
# ═══════════════════════════════════════════════════════════


class TestSessionState:
    """SessionState tracking and summary."""

    def test_decisions_recorded(self, standard_engine):
        standard_engine.evaluate("action one")
        standard_engine.evaluate("action two")
        assert standard_engine.session.action_count == 2
        assert len(standard_engine.session.decisions) == 2

    def test_file_modification_tracking(self, standard_engine):
        standard_engine.record_file_modified("a.py")
        standard_engine.record_file_modified("b.py")
        standard_engine.record_file_modified("a.py")  # duplicate
        assert len(standard_engine.session.files_modified) == 2

    def test_tool_tracking(self, standard_engine):
        standard_engine.record_tool_used("grep")
        standard_engine.record_tool_used("edit")
        standard_engine.record_tool_used("grep")
        assert len(standard_engine.session.tools_used) == 3  # list, not set

    def test_token_tracking(self, standard_engine):
        standard_engine.record_tokens(100)
        standard_engine.record_tokens(200)
        assert standard_engine.session.token_spend == 300

    def test_assumption_tracking(self, standard_engine):
        standard_engine.record_assumption("Python 3.11+", declared=True)
        standard_engine.record_assumption("implicit", declared=False)
        assert len(standard_engine.session.assumptions_declared) == 1
        assert standard_engine.session.assumptions_undeclared == 1

    def test_warning_counting(self, make_engine, make_env):
        env = make_env(can_access_secrets=False)
        engine = make_engine(env=env)
        engine.evaluate("check the secret")
        engine.evaluate("read normal file")
        assert engine.session.warnings_issued == 1

    def test_block_counting(self, make_engine, make_env):
        env = make_env(blocked_paths=["/forbidden"])
        engine = make_engine(env=env)
        engine.evaluate("edit /forbidden/file.py")
        assert engine.session.blocks_issued == 1

    def test_session_summary(self, standard_engine):
        standard_engine.evaluate("action one")
        standard_engine.record_file_modified("f.py")
        standard_engine.record_tool_used("edit")
        standard_engine.record_tokens(50)
        summary = standard_engine.get_session_summary()
        assert summary["total_actions"] == 1
        assert summary["files_modified"] == 1
        assert summary["tools_used"] == 1
        assert summary["token_spend"] == 50
        assert "elapsed_seconds" in summary

    def test_reset_stage_counters(self, make_engine, make_env):
        env = make_env(can_access_secrets=False)
        engine = make_engine(env=env)
        engine.evaluate("check the secret")
        engine.evaluate("edit auth.py")
        engine.evaluate("edit auth.py")
        assert engine.session.warnings_issued >= 1
        assert len(engine.session.retries) >= 1

        engine.session.reset_stage_counters()

        assert engine.session.warnings_issued == 0
        assert engine.session.blocks_issued == 0
        assert len(engine.session.retries) == 0
        # actions_taken is session-level, not reset
        assert engine.session.action_count == 3

    def test_elapsed_seconds(self, standard_engine):
        assert standard_engine.session.elapsed_seconds >= 0


# ═══════════════════════════════════════════════════════════
# PERFORMANCE BENCHMARK
# ═══════════════════════════════════════════════════════════


class TestPerformance:
    """Prove evaluation stays under 1ms."""

    def test_single_evaluation_under_1ms(self, standard_engine):
        """A single evaluate() call must complete in under 1ms."""
        # Warm up (first call may import scanner lazily)
        standard_engine.evaluate("warmup action")

        start = time.perf_counter()
        standard_engine.evaluate("edit auth/views.py")
        elapsed_us = (time.perf_counter() - start) * 1_000_000

        assert elapsed_us < 1000, f"Single evaluation took {elapsed_us:.0f}µs (limit: 1000µs)"

    def test_100_evaluations_average_under_1ms(self, make_engine):
        """Average over 100 calls must stay under 1ms."""
        engine = make_engine(risk_mode=RiskMode.STANDARD)
        engine.evaluate("warmup")

        actions = [
            "edit file.py",
            "read the secret config",
            "delete old logs",
            "run pytest",
            "deploy to staging",
            "edit another_file.py",
            "grep pattern in src/",
            "create migration file",
            "update readme.md",
            "restart server",
        ]

        start = time.perf_counter()
        for i in range(100):
            engine.evaluate(actions[i % len(actions)])
        elapsed_us = (time.perf_counter() - start) * 1_000_000

        avg_us = elapsed_us / 100
        assert avg_us < 1000, f"Average evaluation took {avg_us:.0f}µs (limit: 1000µs)"

    def test_worst_case_under_1ms(self, make_engine, make_env):
        """Worst case: budget + secrets + destructive + session pressure."""
        env = make_env(
            budget=TokenBudget(max_tokens=1000, used_tokens=850),
            can_access_secrets=False,
        )
        engine = make_engine(env=env, risk_mode=RiskMode.GUARDED)
        for i in range(5):
            engine.record_file_modified(f"file_{i}.py")
            engine.record_tool_used(f"tool_{i}")

        engine.evaluate("warmup action")

        start = time.perf_counter()
        engine.evaluate("delete the secret api_key file")
        elapsed_us = (time.perf_counter() - start) * 1_000_000

        assert elapsed_us < 1000, f"Worst-case evaluation took {elapsed_us:.0f}µs (limit: 1000µs)"


    def test_1000_evaluations_sustained_under_1ms(self, make_engine):
        """1000-iteration sustained benchmark: average eval must stay under 1ms."""
        engine = make_engine(risk_mode=RiskMode.STANDARD)

        actions = [
            'edit file.py',
            'delete temp.log',
            'run tests',
            'read config.yaml',
            'write output.json',
            'refactor auth module',
            'deploy to staging',
            'rollback migration',
            'install dependency',
            'update schema',
        ]

        # Warmup
        engine.evaluate('warmup action')

        total_start = time.perf_counter()
        for i in range(1000):
            engine.evaluate(actions[i % len(actions)])
        total_elapsed = time.perf_counter() - total_start

        avg_us = (total_elapsed / 1000) * 1_000_000
        assert avg_us < 1000, (
            f"Average evaluation took {avg_us:.0f}µs over 1000 iterations (limit: 1000µs)"
        )


# ═══════════════════════════════════════════════════════════
# MACRO STRATEGY INTEGRATION
# ═══════════════════════════════════════════════════════════


class TestMacroStrategy:
    """Engine behavior with a macro strategy attached."""

    def test_engine_accepts_macro_strategy(self, make_engine):
        strategy = Option(
            id="opt-1",
            description="Refactor auth module",
            strategy="extract shared logic into base class",
        )
        engine = make_engine(macro_strategy=strategy)
        d = engine.evaluate("edit auth/base.py")
        assert d.verdict == Verdict.PERMIT

    def test_engine_works_without_macro_strategy(self, standard_engine):
        d = standard_engine.evaluate("edit file.py")
        assert d.verdict == Verdict.PERMIT


# ═══════════════════════════════════════════════════════════
# EDGE CASES
# ═══════════════════════════════════════════════════════════


class TestEdgeCases:
    """Boundary conditions and unusual inputs."""

    def test_empty_action_string(self, standard_engine):
        d = standard_engine.evaluate("")
        assert d.verdict in (Verdict.PERMIT, Verdict.WARN)

    def test_very_long_action_string(self, standard_engine):
        action = "edit " + "x" * 10_000
        d = standard_engine.evaluate(action)
        assert d.verdict in (Verdict.PERMIT, Verdict.WARN)

    def test_unicode_action_string(self, standard_engine):
        d = standard_engine.evaluate("edit файл.py")
        assert d.verdict == Verdict.PERMIT

    def test_action_with_newlines(self, standard_engine):
        d = standard_engine.evaluate("edit\nfile.py\nwith newlines")
        assert d.verdict in (Verdict.PERMIT, Verdict.WARN)

    def test_multiple_rules_fire_simultaneously(self, make_engine, make_env, make_ctx):
        """Budget near limit + destructive + low reversibility."""
        env = make_env(budget=TokenBudget(max_tokens=100, used_tokens=90))
        ctx = make_ctx(reversibility=Reversibility.LOW)
        engine = make_engine(env=env, ctx=ctx, risk_mode=RiskMode.STANDARD)
        d = engine.evaluate("delete all data")
        # ESCALATE from destructive:low_reversibility should win over WARN from budget
        assert d.verdict == Verdict.ESCALATE

    def test_zero_budget_blocks_immediately(self, make_engine, make_env):
        env = make_env(budget=TokenBudget(max_tokens=0, used_tokens=0))
        engine = make_engine(env=env)
        d = engine.evaluate("anything")
        assert d.verdict == Verdict.BLOCK
