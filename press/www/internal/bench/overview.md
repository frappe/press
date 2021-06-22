---
title: Build a Bench
---

# Build a Bench

This is information about doctypes required to manage benches and apps on FC
from [desk](https://frappecloud.com/app). Roughly, the build process goes
through these doctypes (that you're concerned with) in order.

App => App Source => Release Group => Deploy Candidate => Bench

To build a bench, we need documents of the following doctypes.

## App

It's simply a master of all apps on FC. Only detail it has is the name of the app.

![App Detail](/assets/press/images/internal/bench/app.png 'App Detail')

## App Source

We use this doc to specify Github _repo_ and _branch_ for an App. An App can have multiple of these.

![App Source Detail](/assets/press/images/internal/bench/app-source.png 'App Source Detail')

## Release Group

This is like a blueprint of a series of benches. It contains a list of Apps and
App Sources as child table.

> Must have frappe as first app.
> You can use `visit dashboard` link in sidebar to see corresponding dashboard view

![Release Group](/assets/press/images/internal/bench/release-group.png 'Release Group')

It also contains a list of servers to deploy your bench on.

## Deploy Candidate (created automatically)

This doc becomes more specific than the Release Group in the sense that it also
has information on which _commit_ of each app you're going to put on your
bench.

![Deploy Candidate](/assets/press/images/internal/bench/deploy-candidate.png 'Deploy Candidate')

> The information of each commit of an App Source is in an App Release doc.

Deploy Candidates are created for each update to the Release Group (could be
update to an app, could be addition/removal of apps, etc..). It is not intended
to deploy all of the ones created. Latest one is deployed when you update bench
from dashboard view.

![Deploy Candidate List](/assets/press/images/internal/bench/deploy-candidate-list.png 'Deploy Candidate List')

You can also manually trigger creation by using `Create Deploy Candidate`
Action on the Release Group.

![Create Deploy Candidate](/assets/press/images/internal/bench/create-deploy-candidate.png 'Create Deploy Candidate')

Use the `Build and Deploy` button to deploy a new Bench.
![](/assets/press/images/internal/bench/build-and-deploy-button.png)

This will create an image that'll be used for creating a bench. In case of any
issue, you can see the log of all commands executed in the Deploy Candidate
doc. `Build` will just create the image, not create a new bench on server.

![Deploy Candidate Log](/assets/press/images/internal/bench/deploy-candidate-log-desk.png)

You can also get live output in the dashboard view.

![Deploy Candidate Dashboard](/assets/press/images/internal/bench/deploy-candidate-dashboard.png 'Deploy Candidate Dashboard')

After build and upload is successful, there should be a link to the new bench
job, which should also be successful for you to use your bench.

![New Bench Job Link](/assets/press/images/internal/bench/new-bench-job-link.png)

## Bench (created automatically)

![New Bench Job](/assets/press/images/internal/bench/new-bench-job.png)

Will be created after successful deploy. Represents a bench on each individual server.

Many can be created for a Deploy Candidate deploy depending on list of servers
in Release Group.

![Bench List](/assets/press/images/internal/bench/bench-list.png)
