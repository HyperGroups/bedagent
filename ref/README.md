# ref

Local reference workspace for codebases that are useful while designing bedagent.

## Layout

```text
ref/
└── ref_repos/   # ignored local clones/worktrees
```

`ref/ref_repos/` is intentionally ignored by Git. Put external repositories,
experimental worktrees, or downloaded references there so they are easy to
search with `rg` without accidentally committing their source code.

## Examples

Clone an external reference repo:

```bash
git clone git@github.com:HyperGroups/sofagent.git ref/ref_repos/sofagent
rg "加载链" ref/ref_repos/sofagent
```

Compare against a reference file:

```bash
diff -u bedagent/SKILL.md ref/ref_repos/sofagent/sofagent/SKILL.md
```

If you only need one file from another branch, `git show other-branch:path` is
still lighter. Use `ref/ref_repos/` when you need repeated local search,
comparison, or broad exploration.
