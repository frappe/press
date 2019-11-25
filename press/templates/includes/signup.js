frappe.ready(function () {
	let page = $("#page-signup");

	function signup() {
		let args = {}
		page.find("form.signup").serializeArray().map(e => {
			args[e.name] = e.value;
		});
		frappe.call({
			method: "press.www.signup.signup",
			args: args,
			type: "POST",
			btn: page.find(".signup-button"),
			callback: () => {
				window.location.replace("dashboard");
			}
		});
	};

	page.find(".signup-button").on("click", () => {
		signup();
	});
});
