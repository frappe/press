// Copyright (c) 2020, Frappe and contributors
// For license information, please see license.txt

frappe.require('assets/press/js/ListComponent.js')

frappe.ui.form.on('Release Group', {
	onload(frm) {
		show_data(
			frm,
			'press.api.bench.versions',
			version_template,
			'bench_versions_block'
		);
		show_data(frm, 'press.api.bench.apps', app_template, 'apps_list_block');
		show_data(
			frm,
			'press.api.bench.recent_deploys',
			deploy_template,
			'recent_deploys_block'
		);
		show_data(frm, 'press.api.bench.versions', sites_template, 'sites_block');
		frm.doc.created_on = frm.doc.apps[0].creation;

		if (frm.is_new()) {
			frm.call('validate_dependencies');
		}
	},
	refresh: function (frm) {
		frm.add_web_link(
			`/dashboard/benches/${frm.doc.name}`,
			__('Visit Dashboard')
		);
		[
			[
				__('Create Deploy Candidate'),
				'press.api.bench.create_deploy_candidate',
			],
		].forEach(([label, method]) => {
			frm.add_custom_button(
				label,
				() => {
					frm
						.call({
							method,
							freeze: true,
							args: {
								name: frm.doc.name,
							},
						})
						.then(({ message }) => {
							frappe.msgprint({
								title: __('New Deploy Candidate Created'),
								indicator: 'green',
								message: __(
									`New <a href="/app/deploy-candidate/${message.name}">Deploy Candidate</a> for this bench was created successfully.`
								),
							});

							frm.refresh();
						});
				},
				__('Actions')
			);
		});
		frm.set_df_property('dependencies', 'cannot_add_rows', 1);
	},
});

// custom html
let version_template = (data) => {
	return `
		<div class="d-flex flex-row justify-between">
			<p>${data.name}</p> 
			<span class="indicator-pill green">${data.sites.length} sites</span>
		</div>
	`;
};

let app_template = (data) => {
	return `
		<div class="d-flex flex-column justify-between">
			<h5>${data.name}</h5>
			<p>${data.repository_owner}/${data.repository}:${data.branch}</p>	
		</div>
	`;
};

let deploy_template = (data) => {
	let date = new Date(data.creation);

	let month = date.toLocaleString('default', { month: 'long' });

	return `
		<div class="d-flex flex-column justify-between">
			<p>
			Deployed on ${date.getDate()} ${month} ${date.getFullYear()}, ${date.getHours()}:${date.getMinutes()} GMT+5:30
			</p>
		</div>
	`;
};

let sites_template = (data) => {
	let bench_name = data.name;
	let sites = data.sites;
	let template = '';

	for (let site of sites) {
		template += `
			<div class="d-flex flex-row justify-between">
				<p class="list-row-col ellipsis list-subject level">${site.name}
				<p class="list-row-col ellipsis hidden-xs">${bench_name}</p>
				<div class="list-row-col ellipsis hidden-xs">
					<p class="indicator-pill ${
						site.status === 'Active' ? 'green' : 'red'
					} ellipsis">${site.status}</p>
				</div>
				<button class="btn btn-outline-primary ellipsis">Visit Site</button>
			</div>
			<hr>
		`;
	}

	return template;
};

// render function
function show_data(frm, method, template, block) {
	frappe.call({
		method: method,
		args: {
			name: frm.docname,
		},
	}).then((res) => {
		new ListComponent(frm.get_field(block).$wrapper, {
            'data': res.message, 
            'template': template
        });    
	})
}
