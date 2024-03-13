$(document).ready(function () {
	if (frappe.boot.setup_complete === 1) {
		// add manage subscription link for all
		add_manage_subscription_link();

		// show subscription banner for trial sites
		let subscription = frappe.boot.subscription_conf;
		if (!subscription || subscription.status === 'Subscribed') {
			return;
		}
		show_banner();
	}
});

function show_banner() {
	let trial_end_date = subscription.trial_end_date;
	let trial_end_message =
		moment(trial_end_date) > moment()
			? `Your trial will end on ${moment(trial_end_date).format(
					'Do MMMM, YYYY',
			  )}.`
			: 'Your trial has ended.';
	let alert = `
			<div class="form-message orange">
				<div class="flex align-center justify-between">
					<span>
						${trial_end_message} Please subscribe to avoid uninterrupted services.
					</span>
					<a class="btn btn-primary" href="${get_subscription_url()}">Subscribe</a>
				</div>
			</div>
		`;
	$('.layout-main-section').before(alert);
}

function add_manage_subscription_link() {
	$('.dropdown-navbar-user .dropdown-menu .dropdown-item:nth-child(2)').after(
		`<a class="dropdown-item" href="${get_subscription_url()}" target="_blank">Manage Subscription</a>`,
	);
}

function get_subscription_url() {
	let sitename = frappe.boot.sitename;
	return `https://frappecloud.com/dashboard-beta/sites/${sitename}`;
}
