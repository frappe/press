$(document).ready(function () {
	if (frappe.boot.setup_complete === 1) {
		let subscription = frappe.boot.subscription_conf;
		if (subscription && subscription.status === 'Subscribed') {
			return;
		}
		let sitename = frappe.boot.sitename;
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
					<a class="btn btn-primary" href="https://frappecloud.com/dashboard-beta/sites/${sitename}">Subscribe</a>
				</div>
			</div>
		`;
		$('.layout-main-section').before(alert);
	}
});
