const trial_end = 15 - frappe.boot.telemetry_site_age;
const trial_end_string =
	trial_end > 1 ? `${trial_end} days` : `${trial_end} day`;

let subscription_string = __(
	`Your trial ends in ${trial_end_string}. Please subscribe to avoid uninterrupted services`,
);

let $floatingBar = $(`
			<div class="flex justify-content-center flex-col p-2"
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
			<p style="margin: auto 0; margin-right: 20px; padding-left: 10px; font-size: 15px;">
				${subscription_string}
			</p>
			<button id="show-dialog" type="button"
				class="
					button-renew
					px-4
					py-2
					border-0
					text-white
				"
				onclick="showBanner()"
				style="
					margin: auto;
					height: fit-content;
					background-color: #171717;
					border-radius: 10px;
					margin-right: 10px
				"
			>
			Subscribe
			</button>
			<!--<a type="button"
				class="dismiss-upgrade text-muted"
				data-dismiss="modal"
				aria-hidden="true"
				style="font-size:30px;
				margin-bottom: 5px;
				margin-right: 10px"
			>×</a>-->
			</div>
`);
let showFloatingBanner = localStorage.getItem('showFloatingBanner');
let banner = true;

if (showFloatingBanner != null) {
	let now = new Date();
	let temp = new Date(showFloatingBanner);

	if (temp.getTime() > now.getTime() && temp.getDate() <= now.getDate()) {
		banner = false;
	}
}

// show only in workspace
const routes = ['/app', '/app/users', '/app/home', '/app/hr'];
if (!routes.includes(window.location.pathname)) {
	banner = false;
}

$(document).ready(function () {
	// check if setup complete
	if (frappe.boot.setup_complete === 1 && banner) {
		$('.layout-main-section').before($floatingBar);
	}
});

function showBanner() {
	const d = new frappe.ui.Dialog({
		title: __('Change Plan'),
		size: 'medium',
	});

	// dismiss banner and add 4 hour dismissal time
	$floatingBar.find('.dismiss-upgrade').on('click', () => {
		const now = new Date();
		const sixHoursLater = new Date(now.getTime() + 4 * 60 * 60 * 1000);

		localStorage.setItem('showFloatingBanner', sixHoursLater);
		$floatingBar.remove();
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
