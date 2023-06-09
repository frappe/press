# Prerequisites

Before we get into writing tests, please make sure you have pre-commit hook for
styling tools setup so CI won't fail from these

Instructions [here](https://github.com/frappe/press/issues/424#issuecomment-1193375098)

# Writing Tests for Press

Writing tests involve running tests locally (duh). So let's get that setup. (You'll only have to do this once)

## Make a test site

Tests can leave fake records. This will pollute your local setup. So, get
yourself a test site. You can get these commands from the CI workflow file too,
but I'll save you some time. You can name the site and set password to whatever.

```sh
bench new-site --db-root-password admin --admin-password admin test_site
bench --site test_site install-app press
bench --site test_site add-to-hosts # in case you wanna call APIs
bench --site test_site set-config allow_tests true
```

Finally, you need to start bench as some of the tests may want to trigger
background jobs, which would fail if background workers aren't there

```sh
bench start
```

As you write tests you'll occasionally want to remove all test data
in your test site from time to time. So, here ya go:

```sh
bench --site test_site reinstall --yes
```

## Writing tests

This is the hard part. Because of Press's dependency with outside world, it's
hard to isolate unit tests to this project. Regardless it's still possible with
plain old python's built in libraries.

Majority of this is done with the help of python's `unittest.mock` library. We
use this library to mock parts of code when referencing things that are out of
Press's control.

Eg: We can mock all Agent Job creation calls by decorating the TestCase class like so

```python
@patch.object(AgentJob, "enqueue_http_request", new=Mock())
class TestSite(unittest.TestCase):
```

We use `patch.object` decorator here so that every instance of `AgentJob`
object will have it's `enqueue_http_request` method be replaced by whatever we
pass in the new argument, which in this case is `Mock()` which does nothing.
You can think of it as a `pass`. But it has other uses as you'll find if you
keep reading.

> Note: Class decorators aren't inherited, so you'll have to do this on all
> classes you want to mock http request creation for Agent Job

Now that we've learned to mock the external things, we can go about mocking
internal things, which forms the basis of testing, which is

1. Make test records
2. Perform operation (i.e Run code that will on production)
3. Test the test records for results

### Making test records

Making test records is also kind of a pain as we have validations all around
code that will need to be passed every time you create a doc. This is too much
cognition. Therefore, we can create utility functions (with sensible defaults)
to make test record of the corresponding Doctype in their own corresponding
test files (for organization reasons). These functions will be doing the bare
minimum to make a valid document of that doctype.

Eg: `create_test_bench` in `test_bench.py` can be imported and used whenever
you need a valid bench (which itself has dependencies on many other doctypes)

You can also add default args to these utility functions as you come across the
need. Just append to end so you won't have to rewrite pre-existing tests.

You write a test by writing a method in the TestCase. Make the method name as
long as you want. Test methods are supposed to test a specific case. When the
test breaks eventually (serving it's purpose), the reader should be able to
tell what it's trying to test is supposed without even having to read the code.
Making the method name small is pointless; we're never going to reference this
method anywhere in code, ever. Eg:

https://github.com/frappe/press/blob/2503e523284fb905eca60acf3271d3fb1dccbc3f/press/press/doctype/site/test_site.py#L215-L228

You can also go the extra mile and write a function docstring. This docstring
will be shown in the output when the testrunner detects that the test has
failed.

### Rerunnability

Not a real word, but I like to be able to re-run my tests without having to
nuke the database. Leaving the database in an "empty state" after every test is
a very easy way to achieve this. This also makes testing for things like count
of docs super easy. Lucky for us there's a method in `TestCase` that's run
after every individual test in the class. It's called `tearDown`.

We can easily do

```python
def tearDown(self):
   frappe.db.rollback()
```

And every doc you create (in foreground at least) will not be committed into the database.

> Note: If the code you're testing calls frappe.db.commit, be sure to mock it
> cuz otherwise docs will get committed till that point regardless.

You can mock certain lines while testing a piece of code with the `patch` decorator too. Eg:

```python
from unittest.mock import MagicMock, patch

# this will mock all the frappe.db.commit calls in server.py while in this test suite
@patch("press.press.doctype.server.server.frappe.db.commit", new=MagicMock)
class TestBench(unittest.TestCase):
```

You can also use the patch decorator on test methods too. Eg:

https://github.com/frappe/press/blob/6dd6b2c8193b04f1aec1601d52ba09ce9dca8dfe/press/tests/test_cleanup.py#L280-L290
The decorator passes the mocked function (which is a `Mock()` object) along as
an argument, so you can later do asserts on it (if you want to).

You can even use the decorator as context manager if you don't want to mock
things for the entirety of the test.

https://github.com/frappe/press/blob/6dd6b2c8193b04f1aec1601d52ba09ce9dca8dfe/press/tests/test_audit.py#L97-L102

> Note: When you use asserts on Mock object, you'll face failures if you're comparing Document objects even if all the fields in the db are the same. This is because when 2 objects are compared only their `id()` is checked by default. If you wish to have intuitive doc equality checking, you can patch `__eq__` of `Document` with comparison of `as_dict` outputs.

Here, we're actually faking the output of the function which usually calls a
remote endpoint that's out of our control by adding the `new` argument to the
method.

> Note: If you need to mock some Callable while preserving it's function, (in
> case you want to do asserts on it, you can use the `wraps` kwarg instead of
> new). Eg:

https://github.com/frappe/press/blob/23711e2799f2d24dfd7bbe2b6cd148f54f4b253b/press/press/doctype/database_server_mariadb_variable/test_database_server_mariadb_variable.py#L138-L155

Here, we check what args was Ansible constructor was called with.

That's pretty much all you need to write safe, rerunnable tests for Press. You
can checkout https://docs.python.org/3/library/unittest.mock.html for more
things you can do with the standard python libraries. If your editor and
plugins are setup configured nicely, you can even do TDD with ease.

> Protip: When you have test records you want across a TestCase, then you can
> simply use the create the test record in `setUp` method of the same. The test
> records can be assigned to member variables. Eg:

```python
def setUp(self):
   self.team = create_test_team()
```

### Background jobs

Since background jobs are forked off of a different process, our mocks and
patches are not going to hold there. Not only that, but we can't
control/predict when the background job will run and finish. So, when your code
involves creating a background job, we can simply mock the call so that it runs
in foreground instead. There's a utility method you can use to achieve this with ease:

https://github.com/frappe/press/blob/23711e2799f2d24dfd7bbe2b6cd148f54f4b253b/press/press/doctype/database_server_mariadb_variable/test_database_server_mariadb_variable.py#L12

https://github.com/frappe/press/blob/23711e2799f2d24dfd7bbe2b6cd148f54f4b253b/press/press/doctype/database_server_mariadb_variable/test_database_server_mariadb_variable.py#L104-L108

## Running tests

You can run all of the tests with the following command.

```sh
bench --site test_site run-tests --app press
```

But you'll never have to. That's what CI is for. Instead, you'll mostly want to use:

```sh
bench --site test_site run-tests --app press --module press.press.doctype.some_doctype.test_some_doctype
```

This is because while writing bugs, your changes will mostly affect that one
module only and since we don't have many tests to begin with, it won't take
very long to run a module's test by itself anyway. Give your eyes a break while this happens.

You can also run individual test with:

```sh
bench --site test_site run-tests --module  press.press.doctype.some_doctype.test_some_doctype --test test_very_specific_thing
```

You most likely won't enjoy running commands manually like this. So you'd want
to check out [this vim plugin](https://github.com/ankush/frappe_test.vim/) or
[this vscode plugin](https://marketplace.visualstudio.com/items?itemName=AnkushMenat.frappe-test-runner)

> Note: frappe_test plugin doesn't populate vim's quickfix list yet. Though
> Frappe's test runner output isn't very pyunit errorformat friendly, you can
> still make it work with a [custom errorformat](https://github.com/balamurali27/dotfiles/blob/85dc18a/.config/nvim/after/plugin/frappe.vim#LL10C1-L10C128) and some hacks to [set makeprg](https://github.com/balamurali27/dotfiles/blob/0bcd6270770d0b67b63fc0ea308e6834fefda5a6/.config/nvim/init.vim#L150C7-L163)

# References

- https://frappeframework.com/docs/v14/user/en/testing
- https://docs.python.org/3/library/unittest.mock.html
- https://learnvim.irian.to/basics/compile
