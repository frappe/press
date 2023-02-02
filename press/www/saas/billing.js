let subscription_string = __('Your subscription will end soon and the site will be suspended. Please subscribe before that for uninterrupted services');
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
    </div>
    </div>
`);
$('footer').append($floatingBar);

const d = new frappe.ui.Dialog({
	title: __('Manage your subscriptions'),
	size: 'large',
});

$('#show-dialog').on('click', function () {
	d.show();
});

$(d.body).html(`
	<div id="wrapper" style="position:relative">
		<iframe 
			src="https://frappecloud.com/saas/billing.html?secret_key=${frappe.boot.subscription_key}" 
			style="position: relative; top: 0px; width: 100%; height: 60vh;" 
			frameborder="0"
		>
	</div>
`);

