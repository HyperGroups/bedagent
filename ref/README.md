# ref

Reference workspace for codebases that are useful while designing bedagent.

## Layout

```text
ref/
└── ref_repos/   # committed source snapshots for GitHub browsing
```

`ref/ref_repos/` stores plain source snapshots. These folders are committed so
they are visible on GitHub and easy to inspect with `rg`, but nested `.git`
metadata and generated artifacts must be stripped before committing.

## Examples

Clone an external reference repo, then strip nested Git metadata before commit:

```bash
git clone git@github.com:HyperGroups/sofagent.git ref/ref_repos/sofagent
git -C ref/ref_repos/sofagent rev-parse HEAD > ref/ref_repos/sofagent/REF_SNAPSHOT.txt
rm -rf ref/ref_repos/sofagent/.git
rg "加载链" ref/ref_repos/sofagent
```

Compare against a reference file:

```bash
diff -u bedagent/SKILL.md ref/ref_repos/sofagent/sofagent/SKILL.md
```

If you only need one file from another branch, `git show other-branch:path` is
still lighter. Use `ref/ref_repos/` when you need repeated local search,
comparison, or broad exploration.

## Historical snapshots

When bedagent needs a design reset, keep the old working implementation as a
reference snapshot instead of mixing it with the new active code:

```bash
ref/ref_repos/bedagent-bootstrap/
```

This snapshot is for `rg`, `diff`, and broad reference only. Do not edit it as
the source of truth. If a future change needs code from the snapshot, copy the
specific idea or file intentionally into the active tree and commit that change
normally.
