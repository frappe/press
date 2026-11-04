# Pull request guidelines

Guidelines for opening pull requests in this project.

Open pull requests against the `develop` branch, not `master`. Add the
`backport-master` label to each pull request.

Never hard-wrap the PR description at 80 characters, or at any width. GitHub
renders the description as markdown and wraps it for the reader. Hand-wrapped
lines break when the reader changes the width of the box, and they are hard to
edit. Let each paragraph run on one line. The 72-character limit applies to the
commit header only, not to the PR body.

Attach screenshots to the pull request directly. Do not commit a screenshot to
the repository and link it with a `raw.githubusercontent.com` URL. GitHub
deletes the branch when the pull request merges. Every link to that branch then
gives a 404, and the description shows a broken image to each reader. The
screenshots in [press#7405](https://github.com/frappe/press/pull/7405) broke
this way. Paste each image into the description box instead. GitHub uploads it
and keeps it for the life of the pull request.
