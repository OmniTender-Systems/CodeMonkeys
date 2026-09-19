# Task: Implement git worktree isolation for concurrent subagent tasks (Issue #244)

The CodeMonkeys server spawns sub-agents that all operate on the same working directory. When multiple sub-agents run concurrently, they can conflict on files.

## Goal
Give each sub-agent an isolated git worktree so concurrent tasks don't clobber each other.

## Steps
1. Read `docs/STATE.md`, `docs/IDEATION.md`, and issue #244
2. Find the existing subagent spawning code in `server.py` (function `run_subagent`)
3. Design worktree creation/cleanup around subagent lifecycle
4. Implement: create a worktree per subagent, clean up on completion
5. Add tests in `tests/test_subagent_worktree.py`
6. Run full test suite to verify nothing breaks
