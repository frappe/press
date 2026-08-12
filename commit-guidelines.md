# Commit guidelines

Guidelines for writing good commit messages in this project.

## Use one convention

Use [Conventional Commits](https://www.conventionalcommits.org/).

- Use sentence case for the title and the body. The first letter of the
  description (the word right after the scope's `:`) is capital.
- Always add scopes.
- Use lowercase for the type and scope. Not title or capital. Not camel case.
- Hyphenate. Don't use snake case.

Example: `fix(site): Mark bahrain backups unavailable before offsite delete`

## Write descriptive messages

Messages must give sufficient information about the change and the context
of the change. Changes like these don't add anything:

```
fix: added required doctypes
fix: updated cluster.py
```

If the title isn't enough, write a body.

## Write bodies

A body is always better.

Most changes aren't trivial. Try to explain why you're making the change.

## Keep it short

A body is a few lines, not a page. Two to five lines is usually enough.

Say why the change is being made, and stop. Don't recap what the diff
already shows, don't describe how the tests are set up, and don't narrate
what you tried and reverted along the way.

## Explain choices

You are making choices all the time. Explain why that choice. Why not an
alternative?

One line for the alternative is enough. `Kept it inline because an
enqueued job leaves no record if it fails` says as much as a paragraph.

## Link references

Some references might be lost over time. We'll take what we can get. Link
what's relevant:

- Sentry issues / events
- Error logs
- Reports (error log analysis, stuck scheduled jobs, etc.)
- Insights charts / dashboards
- Code (commits, lines, PRs)
- External (docs, blogs, StackOverflow)

Some of this can go in the PR comments. But keep some information in the
commit messages as well.
