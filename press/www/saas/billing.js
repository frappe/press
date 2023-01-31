let subscription_string = __('Your subscription will end in x days');
let $floatingBar = $(`
    <div 
			class="shadow sm:rounded-lg py-2" 
			style="
				position:fixed; 
				left: 245px; 
				bottom:20px; 
				width:70%; 
				margin: auto; 
				border-radius: 10px; 
				background-color: #F7FAFC; 
				z-index: 1">
    <div 
			style="display: flex; align-items: center; justify-content: space-between"
			class="text-muted">
    <p style="margin-left: 20px; margin-top:5px; font-size: 17px">
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
				hover:bg-indigo-700 
				focus:outline-none 
				focus:ring-offset-2 
				focus:ring-indigo-500
			" 
			style="
				background-color: #007bff; 
				border-radius: 5px; 
				margin-left:650px; 
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

