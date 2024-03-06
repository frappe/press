$(document).ready(function () {
	if (frappe.boot.setup_complete === 1) {
		let subscription = frappe.boot.subscription_conf;
		if (subscription && subscription.status === 'Subscribed') {
			return;
		}
		let sitename = frappe.boot.sitename;
		let trial_end = 15 - frappe.boot.telemetry_site_age;
		let trial_end_message = '';
		if (trial_end <= 0) {
			trial_end_message = 'Your trial has ended.';
		} else if (trial_end === 1) {
			trial_end_message = 'Your trial will end in 1 day.';
		} else {
			trial_end_message = `Your trial will end in ${trial_end} days.`;
		}
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
