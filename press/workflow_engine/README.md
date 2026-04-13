# Press Workflow Engine

An asynchronous workflow engine for Frappe. Define long-running workflows with automatic task tracking, state persistence, and fault tolerance using simple decorators.

---

## Quick Start

### 1. Inherit from WorkflowBuilder

```python
from press_agent_manager.workflow_engine.doctype.press_workflow.decorators import flow, task
from press_agent_manager.workflow_engine.doctype.press_workflow.workflow_builder import WorkflowBuilder


class MyDoctype(WorkflowBuilder):
    pass
```

### 2. Define tasks with `@task`

```python
class MyDoctype(WorkflowBuilder):

    @task
    def fetch_data(self) -> dict:
        """Fetch data from external API"""
        response = requests.get(self.api_url)
        return response.json()

    @task
    def process_item(self, item: dict) -> dict:
        """Process a single item"""
        return {"id": item["id"], "processed": True}
```

### 3. Define a flow with `@flow`

```python
class MyDoctype(WorkflowBuilder):

    # ... tasks defined above ...

    @flow
    def run_pipeline(self) -> dict:
        """Main processing pipeline"""
        data = self.fetch_data()

        results = []
        for i, item in enumerate(data["items"]):
            result = self.process_item.with_task_id(f"item_{i}")(item)
            results.append(result)

        self.status = "Completed"
        self.save(ignore_permissions=True)
        return {"count": len(results)}
```

### 4. Start the workflow

```python
doc = frappe.get_doc("My Doctype", "DOC-001")

# Run as background workflow (async)
workflow_name = doc.run_pipeline.run_as_workflow()

# Or just call it directly (sync) - works like a normal method
result = doc.run_pipeline()
```

The engine handles task execution, persistence, retries, and resumption automatically.

---

## Decorators

### `@task`

Marks a method as a workflow task.

**In workflow mode** (via `.run_as_workflow()`): Tasks are enqueued for background execution, results are persisted, and the workflow pauses until the task completes.

**In normal mode** (direct call): Behaves like a regular method - runs synchronously and returns immediately.

```python
class MyDoctype(WorkflowBuilder):

    @task
    def my_task(self, arg1: int, arg2: str) -> dict:
        """First line of docstring becomes the step title in UI"""
        return {"result": arg1 + len(arg2)}

# Both work:
doc.my_task(1, "hello")              # sync, normal method call
doc.some_flow.run_as_workflow()      # async, my_task tracked as workflow step
```

### `@flow`

Marks a method as a workflow entry point.

**In workflow mode** (via `.run_as_workflow()`): Creates a `Press Workflow` document, discovers all task calls via AST inspection, and tracks them as steps.

**In normal mode** (direct call): Runs synchronously like a normal method.

```python
class MyDoctype(WorkflowBuilder):

    @task
    def some_task(self, x: int) -> int:
        return x * 2

    @flow
    def my_workflow(self, x: int) -> dict:
        """My workflow description"""
        result = self.some_task(x)
        return {"done": True, "result": result}

# Both work:
doc.my_workflow(42)                      # sync
doc.my_workflow.run_as_workflow(42)      # async, creates Press Workflow
```

---

## Sharing State Between Tasks

> **Important**: Do NOT use in-memory structures to share state between tasks.

Since tasks run in separate background jobs, things like `self.some_var`, `frappe.local.xyz`, or `frappe.flags.xyz` won't persist between task executions. By the time Task B runs, whatever Task A stored in memory is gone.

**Wrong:**

```python
class MyDoctype(WorkflowBuilder):

    @task
    def step_one(self):
        self.intermediate_data = {"important": "stuff"}  # Won't work!
        frappe.flags.my_data = [1, 2, 3]                 # Won't work!

    @task
    def step_two(self):
        print(self.intermediate_data)  # AttributeError or stale data
```

**Correct - use `self.kv`:**

The key-value store persists data to the database and works both in workflow mode and normal execution:

```python
class MyDoctype(WorkflowBuilder):

    @task
    def step_one(self):
        self.kv.set("intermediate_data", {"important": "stuff"})
        self.kv.set("items", [1, 2, 3])

    @task
    def step_two(self):
        data = self.kv.get("intermediate_data")  # {"important": "stuff"}
        items = self.kv.get("items")             # [1, 2, 3]

        # Clean up when done
        self.kv.delete("intermediate_data")
```

The `self.kv` store:

- Works in both workflow mode and normal sync calls
- Persists any picklable Python object
- Is scoped to the workflow instance

---

## Nested Tasks and Loops

### Using `.with_task_id()` in loops

When calling the same task multiple times (like in a loop), you need unique task IDs to prevent deduplication issues:

```python
class MyDoctype(WorkflowBuilder):

    @task
    def process_item(self, item: dict) -> dict:
        return {"processed": item["id"]}

    @flow
    def process_all(self) -> list:
        results = []
        for i, item in enumerate(self.items):
            # Each iteration needs a unique task ID
            result = self.process_item.with_task_id(f"item_{i}")(item)
            results.append(result)
        return results
```

Without `.with_task_id()`, the engine would see identical signatures and return cached results from the first call.

### Nested task calls

Tasks can call other tasks:

```python
class MyDoctype(WorkflowBuilder):

    @task
    def multiply(self, a: int, b: int) -> int:
        return a * b

    @task
    def power(self, base: int, exponent: int) -> int:
        """Calculate power using nested multiply calls"""
        result = 1
        for i in range(exponent):
            result = self.multiply.with_task_id(f"mult_{i}")(result, base)
        return result
```

The engine handles the nesting - parent tasks pause while nested tasks execute, then resume.

---

## Warning: Never Catch `PressWorkflowTaskEnqueued`

The workflow engine uses `PressWorkflowTaskEnqueued` internally to pause execution when a task is enqueued. If you catch this exception, the workflow will hang forever or behave unpredictably.

**Wrong:**

```python
class MyDoctype(WorkflowBuilder):

    @task
    def my_task(self):
        try:
            self.some_other_task()
        except Exception as e:  # This catches PressWorkflowTaskEnqueued!
            print(f"Error: {e}")
```

**Correct:**

```python
from press_agent_manager.workflow_engine.doctype.press_workflow.exceptions import (
    PressWorkflowTaskEnqueued,
)

class MyDoctype(WorkflowBuilder):

    @task
    def my_task(self):
        try:
            self.some_other_task()
        except PressWorkflowTaskEnqueued:
            raise  # Always re-raise this
        except Exception as e:
            print(f"Error: {e}")
```

---

## Checking Workflow Status

```python
workflow = frappe.get_doc("Press Workflow", workflow_name)

# Basic info
print(workflow.status)    # "Queued", "Running", "Success", "Failure", "Fatal"
print(workflow.stdout)    # Captured print output
print(workflow.duration)  # Total execution time

# Get result (raises if still running or failed)
# If the flow failed, get_result() re-raises the original exception
from press_agent_manager.workflow_engine.doctype.press_workflow.exceptions import (
    PressWorkflowRunningError,
    PressWorkflowFailedError,
    PressWorkflowFatalError,
)

try:
    result = workflow.get_result()
except PressWorkflowRunningError:
    print("Still running...")
except PressWorkflowFailedError as e:
    print(f"Failed: {e}")
except PressWorkflowFatalError as e:
    # Fatal = internal issue or bug in the workflow engine itself
    # (not an error in your flow code)
    print(f"Fatal error: {e}")
except Exception as e:
    # The actual exception raised during flow execution
    print(f"Original error: {e}")
```

### Viewing step progress

```python
for step in workflow.steps:
    print(f"{step.step_title}: {step.status}")
```

---

## How It Works

### Workflow creation

When you call `.run_as_workflow()`:

1. The decorator parses the flow method's AST to find `self.task_name()` calls
2. Creates a `Press Workflow` doc linked to your document
3. Pre-registers discovered tasks as workflow steps
4. Enqueues the workflow via `frappe.enqueue_doc()`

### Task execution

When the workflow runs and hits a `@task` call:

1. Generates a signature from method name + arguments (+ optional task_id)
2. Checks if a task with that signature already exists:
   - **Exists and succeeded**: Returns cached result immediately
   - **Exists and running/queued**: Raises `PressWorkflowTaskEnqueued` to pause
   - **Doesn't exist**: Creates new `Press Workflow Task` and enqueues it
3. The workflow pauses until the task completes

### Resumption

After a task finishes:

1. It re-enqueues its parent (either another task or the main workflow)
2. Parent runs again, hits the same task call
3. This time the task exists and succeeded, so it returns the cached result
4. Execution continues to the next task

### Deduplication

Tasks are deduplicated by signature:

- `method_name` + canonicalized `(args, kwargs)` + optional `task_id`
- Same signature = same task (returns cached result)
- Different params or task_id = new task

---

## Configuration

Set queue names in `site_config.json`:

```json
{
  "press_workflow_queue": "short",
  "press_workflow_task_queue": "default"
}
```

## Tips

- First line of a task/flow docstring becomes the step title in the UI
- Always use `.with_task_id()` when calling the same task multiple times
- Use `self.kv` for sharing data between tasks, never in-memory variables
- Tasks that are never reached (due to conditionals) are marked as "Skipped"
- Exceptions in tasks are captured and re-raised when the workflow resumes
