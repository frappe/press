let subscription_string = __(
	'Your subscription will end soon and the site will be suspended. Please subscribe before that for uninterrupted services',
);
let $floatingBar = $(`
    <div class="flex justify-content-center" style="width: 100%;">
    <div class="flex justify-content-center flex-col shadow rounded p-2"
			style="
				width: 80%;
				background-color: #e0f2fe;
				position: fixed;
				bottom: 20px;
				z-index: 1;">
    <p style="margin: auto 0; margin-right: 20px; padding-left: 10px; font-size: 15px;">
			${subscription_string}
		</p>
    <button id="show-dialog" type="button"
			class="
				button-renew
				px-4
				py-2
				border
				border-transparent
				text-white
			"
			style="
				margin: auto;
				height: fit-content;
				background-color: #007bff;
				border-radius: 5px;
				margin-right: 10px
			"
		>
		Subscribe
		</button>
				<a type="button" class="dismiss-upgrade text-muted" data-dismiss="modal" aria-hidden="true" style="font-size:30px; margin-bottom: 5px; margin-right: 10px">×</a>

    </div>
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

let siteAge = frappe.boot.telemetry_site_age || 7;
if (siteAge < 3) {
	banner = false;
}

if (frappe.boot.setup_complete === 1 && banner) {
	// check if setup complete
	$('footer').append($floatingBar);
}

const d = new frappe.ui.Dialog({
	title: __('Manage your subscriptions'),
	size: 'large',
});

$('#show-dialog').on('click', function () {
	d.show();
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
		src="http://p.site:8080/dashboard/checkout?secret_key=${frappe.boot.subscription_conf.secret_key}"
			style="position: relative; top: 0px; width: 100%; height: 60vh;"
			frameborder="0"
		>
	</div>
`);
