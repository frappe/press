# Commit guidelines

Guidelines for writing good commit messages in this project.

## Use one convention

Use [Conventional Commits](https://www.conventionalcommits.org/).

- Use sentence case for the title and the body. The first letter of the
  description, the word directly after the `:` of the scope, is a capital.
- Always add scopes.
- Use lowercase for the type and the scope. Not title case, not capitals, not
  camel case.
- Hyphenate. Do not use snake case.

Example: `fix(site): Mark bahrain backups unavailable before offsite delete`

## Write descriptive messages

A message must give sufficient information about the change and about the
context of the change. Messages like these add nothing:

```
fix: added required doctypes
fix: updated cluster.py
```

If the title is not sufficient, write a body.

## Write bodies

A body is always better.

Most changes are not trivial. Explain why you make the change.

## Keep it short

A body is a few lines, not a page. Two to five lines is usually sufficient.

Say why the change is necessary, and stop. Do not repeat what the diff already
shows. Do not describe the test setup. Do not tell the reader what you tried and
then reverted.

## Explain choices

You make choices all the time. Explain why you made that choice. Why not an
alternative?

One line for the alternative is sufficient. `Kept it inline because an enqueued
job leaves no record if it fails` says as much as a paragraph.

## Link references

References can become lost with time. Link what is relevant:

- Sentry issues and events
- Error logs
- Reports: error log analysis, stuck scheduled jobs, and more
- Insights charts and dashboards
- Code: commits, lines, pull requests
- External pages: docs, blogs, StackOverflow

Some of this can go in the PR comments. But keep some of the information in the
commit messages also.
