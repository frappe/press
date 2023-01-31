let subscription_string = __("Your subscription will end in x days");
let $bar = $(`
    <div class="shadow sm:rounded-lg py-2" style="position:fixed; left: 145px; bottom:20px; width:80%; margin: auto; border-radius: 10px; background-color: #F7FAFC; z-index: 1">
    <div style="display: inline-flex; align-items: center", class="text-muted">
    <p style="margin-left: 20px; margin-top:5px; font-size: 17px">${subscription_string}</p>
    <button id="show-dialog" type="button" class="button-renew px-4 py-2 border border-transparent text-white hover:bg-indigo-700 focus:outline-none focus:ring-offset-2 focus:ring-indigo-500" style="background-color: #007bff; border-radius: 5px; margin-left:650px; margin-right: 10px">Subscribe</button>
    <a type="button" class="dismiss-upgrade text-muted" data-dismiss="modal" aria-hidden="true" style="font-size:30px; margin-bottom: 5px; margin-right: 10px">\xD7</a>
</div>
`);
$(".main-section").append(frappe.templates["xnomad"])
$("footer").append($bar);
