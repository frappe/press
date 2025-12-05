---
route: marketplace
allow_guest: 1
published: 1
---

## The Marketplace App DocType

The main master for marketplace is the “Marketplace App” DocType around which all the other doctypes revolve around. 

## Release Management

When the developer “Publish”es a release (by using the steps described in Managing your Marketplace App (frappecloud.com)), an “App Release Approval Request'' is created, which I review (there is an assignment rule that assigns it to just me as of now). For apps I trust (like POSAwesome), I approve the releases blindly, for new apps I look at the diff if the repo is open source or have to use the code server to look into the app.

## Approving a release

Just a click my friend, just a click.

Go to the “App Release Approval Request” list and find the release you want to approve. 




Once approved, the new release will be available for deployment on bench groups (RGs)!

> Note: Unapproved releases are only available on Release Groups that belong to the owner of the app.

## Server Script for Auto-approving of App Releases for Marketplace App

There is a Server Script that auto-approves releases (sets the status of the ‘App Release’ doc to ‘Approved’) for all the apps belonging to team@erpnext.com (Auto approve frappe/erpnext releases (frappecloud.com)).


## Publishing of New Apps

It all starts with the developer of the app enabling developer mode and adding the app to be published via dashboard as per the instructions written here: Publishing an App to Marketplace (frappecloud.com). In the backend the “Marketplace App” master is created and its status is set to “Draft”. 

Then the process is roughly:

- General review of what the app is, what it does and will it be any useful to users other than the publisher herself.
- Check for missing fields like description, logo and long description.
- Review the code: look for security issues and suspicious scripts / executables mainly.
- Fixing the grammatical errors and formatting in a long description :).

After the review is done, there are 2 steps we need to do in order to “Publish” the app. First of all click on the “Add to Public Bench Groups” button on the Marketplace App form. This will add the app source(s) of this app to respective public bench groups. For example, if the app supports two versions having sources: source A & source B (check the “versions” child table for more)

