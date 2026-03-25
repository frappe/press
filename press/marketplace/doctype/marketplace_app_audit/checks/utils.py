import ast


# utility functions
def _extract_string_assignment(filepath: str, variable_name: str) -> str | None:
	"""Extract the string value of a top-level assignment like `app_name = "press"` via AST."""
	with open(filepath) as f:
		tree = ast.parse(f.read())

	for node in tree.body:
		if not isinstance(node, ast.Assign):
			continue
		for target in node.targets:
			if (
				isinstance(target, ast.Name)
				and target.id == variable_name
				and isinstance(node.value, ast.Constant)
				and isinstance(node.value.value, str)
			):
				return node.value.value
	return None


def _get_call_name(func_node: ast.expr) -> str | None:
	"""Return a readable name for a Call's func node, or None if it's a safe pattern."""
	if isinstance(func_node, ast.Name):
		return func_node.id
	if isinstance(func_node, ast.Attribute):
		return f"...{func_node.attr}"
	return None


def _extract_top_level_assignments(tree: ast.Module) -> dict[str, ast.expr]:
	"""Return {variable_name: value_node} for all top-level assignments."""
	assignments = {}
	for node in tree.body:
		if isinstance(node, ast.Assign):
			for target in node.targets:
				if isinstance(target, ast.Name):
					assignments[target.id] = node.value
	return assignments


def _extract_dict_string_keys(node: ast.expr) -> list[str]:
	if not isinstance(node, ast.Dict):
		return []
	return [key.value for key in node.keys if isinstance(key, ast.Constant) and isinstance(key.value, str)]
