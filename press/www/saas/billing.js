function calculate_trial_end_days() {
	// try to check for trial_end_date in frappe.boot.subscription_conf
	if (frappe.boot.subscription_conf.trial_end_date) {
		const trial_end_date = new Date(
			frappe.boot.subscription_conf.trial_end_date,
		);
		const today = new Date();
		const diffTime = trial_end_date - today;
		const diffDays = Math.ceil(diffTime / (1000 * 60 * 60 * 24));
		return diffDays;
	} else {
		return 15 - frappe.boot.telemetry_site_age;
	}
}

const trial_end_days = calculate_trial_end_days();

const trial_end_string =
	trial_end_days > 1 ? `${trial_end_days} days` : `${trial_end_days} day`;

let subscription_string = __(
	`Your trial ends in ${trial_end_string}. Please subscribe for uninterrupted services`,
);

let $floatingBar = $(`
			<div class="flex justify-content-center flex-col px-2"
				style="
					background-color: rgb(254 243 199);
					border-radius: 10px;
					margin-bottom: 20px;
					z-index: 1;"
			>
			<svg xmlns="http://www.w3.org/2000/svg" width="24"
				height="24"
				viewBox="0 0 24 24"
				fill="none"
				stroke="currentColor"
				stroke-width="1.5"
				stroke-linecap="round"
				stroke-linejoin="round"
				class="feather feather-alert-triangle my-auto"
			>
				<path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"></path>
				<line x1="12" y1="9" x2="12" y2="13"></line><line x1="12" y1="17" x2="12.01" y2="17"></line>
			</svg>
			<p style="margin: auto 0; margin-right: 20px; padding-left: 10px;">
				${subscription_string}
			</p>
			<button id="show-dialog" type="button"
				class="
					button-renew
					px-2
					py-1
				"
				onclick="showBanner()"
				style="
					margin: auto;
					height: fit-content;
					background-color: transparent;
					border: 1px solid #171717;
					color: #171717;
					border-radius: 8px;
					margin-right: 8px;
					font-size: 13px;
				"
			>
			Subscribe
			</button>
			<a type="button"
				class="dismiss-upgrade text-muted"
				data-dismiss="modal"
				aria-hidden="true"
				style="font-size:24px;
				margin-bottom: 5px;
				margin-right: 5px"
			>×</a>
			</div>
`);

$(document).ready(function () {
	if (frappe.boot.setup_complete === 1) {
		if (
			!frappe.is_mobile() &&
			frappe.boot.subscription_conf.status !== 'Subscribed' &&
			trial_end_days > 0
		) {
			$('.layout-main-section').before($floatingBar);

			$floatingBar.find('.dismiss-upgrade').on('click', () => {
				$floatingBar.remove();
			});
		}
		add_frappe_cloud_dashboard_link();
	}
});

function add_frappe_cloud_dashboard_link() {
	$('.dropdown-navbar-user .dropdown-menu .dropdown-divider').before(
		`<a class="dropdown-item" href="https://frappecloud.com/dashboard/" target="_blank">Log In to Frappe Cloud</a>`,
	);
}

function showBanner() {
	const d = new frappe.ui.Dialog({
		title: __('Change Plan'),
		size: 'medium',
	});

	$(d.body).html(`
		<div id="wrapper" style="position:relative">
			<iframe
				src="https://frappecloud.com/dashboard/checkout/${frappe.boot.subscription_conf.secret_key}"
				style="position: relative; top: 0px; width: 100%; height: 60vh;"
				frameborder="0"
			>
		</div>
	`);

	d.show();
}
