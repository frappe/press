// Copyright (c) 2025, Frappe and contributors
// For license information, please see license.txt

frappe.ui.form.on('Downtime Analysis', {
	refresh(frm) {
		frm.disable_save();
		$('.section-head, .section-body').css('max-width', 'none');
		frm.add_custom_button(__('Fetch Report'), function () {
			frm.call('fetch_report');
		});
		// Load start_date and end_date from localstorage
		const stored_start_date = localStorage.getItem(
			'downtime_analysis_start_date',
		);
		const stored_end_date = localStorage.getItem('downtime_analysis_end_date');
		if (stored_start_date) {
			frm.set_value('start_date', stored_start_date);
		}
		if (stored_end_date) {
			frm.set_value('end_date', stored_end_date);
		}
	},
	start_date(frm) {
		localStorage.setItem('downtime_analysis_start_date', frm.doc.start_date);
		fetch_report(frm);
	},
	end_date(frm) {
		localStorage.setItem('downtime_analysis_end_date', frm.doc.end_date);
		fetch_report(frm);
	},
});

function fetch_report(frm) {
	if (frm.doc.name && frm.doc.start_date && frm.doc.end_date) {
		// validate if start_date is before end_date
		if (frm.doc.start_date > frm.doc.end_date) {
			frappe.msgprint(__('Start Date must be before End Date'));
			frm.set_value('start_date', null);
			frm.set_value('end_date', null);
			frm.set_value('status', null);
			return;
		}
		frm.call('fetch_report').then(() => {
			render_reports(frm);
		});
	}
}

function render_reports(frm) {
	if (frm.doc.status !== 'Report Available' || !frm.doc.raw_data) {
		return;
	}
	const report = JSON.parse(frm.doc.raw_data);
	if (report?.server) {
		render_server_downtime_report(frm, report.server);
	}
	if (report?.site) {
		render_site_downtime_report(frm, report.site);
	}

	if (report?.site && report?.site?.problematic_sites_analysis_report) {
		render_problematic_site_analysis(
			frm,
			report?.site?.problematic_sites_analysis_report,
		);
	}
}

const column_header_map = {
	cluster: 'Cluster',
	server: 'Server',
	group: 'Group',
	site: 'Site',
	status: 'Status',
	status_code: 'Status Code',
	error: 'Error',
	proxy_server: 'Proxy Server',
	redirects: 'Redirects',
	total_downtime: 'Total Downtime',
	contribution_to_server_downtime: '% of Server Downtime',
	contribution_to_cluster_downtime: '% of Cluster Downtime',
	contribution_to_total_downtime: '% of Total Downtime',
};

const data_transformer_map = {
	total_downtime: (value) => humanize_seconds(value),
	downtime: (value) => humanize_seconds(value),
	contribution_to_cluster_downtime: (value) => `${value.toFixed(2)}`,
	contribution_to_total_downtime: (value) => `${value.toFixed(2)}`,
};

function render_server_downtime_report(frm, report) {
	let report_div = $('#server_downtime_report');
	// Clean up previous report
	report_div.empty();
	report_div.css({
		display: 'flex',
		'flex-direction': 'column',
		gap: '10px',
	});

	// Servers with Complete Downtime
	render_table_section(
		report_div[0],
		'Servers with Complete Downtime',
		report.servers_with_complete_downtime,
		{
			exclude_keys: ['dates'],
			transform: data_transformer_map,
			column_header: column_header_map,
		},
	);

	// Top 20 Servers with Highest Downtime
	const top_20_down_servers_cluster_header = document.createElement('h5');
	top_20_down_servers_cluster_header.innerText =
		'Top 20 Servers with Highest Downtime per Cluster';
	report_div.append(top_20_down_servers_cluster_header);

	for (const cluster of report.clusters_sorted_by_downtime) {
		let data = report.top_20_servers_with_highest_downtime_per_cluster[cluster];
		if (!data || data.length === 0) continue;

		render_table_section(report_div[0], `${cluster} Cluster`, data, {
			exclude_keys: [],
			transform: data_transformer_map,
			column_header: column_header_map,
		});
	}
}

function render_site_downtime_report(frm, report) {
	let report_div = $('#site_downtime_report');
	// Clean up previous report
	report_div.empty();
	report_div.css({
		display: 'flex',
		'flex-direction': 'column',
		gap: '10px',
	});

	// Sites with Complete Downtime
	render_table_section(
		report_div[0],
		'Sites with Complete Downtime',
		report.sites_with_complete_downtime,
		{
			exclude_keys: ['dates'],
			transform: data_transformer_map,
			column_header: column_header_map,
		},
	);

	// Top k Sites with Highest Downtime of each cluster
	const top_k_sites_with_highest_downtime_of_each_cluster_header =
		document.createElement('h5');
	top_k_sites_with_highest_downtime_of_each_cluster_header.innerText =
		'Top k Sites with Highest Downtime per Cluster';
	report_div.append(top_k_sites_with_highest_downtime_of_each_cluster_header);

	for (const cluster of Object.keys(
		report.top_k_sites_with_highest_downtime_per_cluster,
	)) {
		// Sort by highest downtimes
		let data = report.top_k_sites_with_highest_downtime_per_cluster[cluster];
		if (!data || data.length === 0) continue;

		render_table_section(report_div[0], `${cluster} Cluster`, data, {
			exclude_keys: [],
			transform: data_transformer_map,
			column_header: column_header_map,
		});
	}

	// Top 20 servers with Highest Downtime of each cluster
	const top_20_servers_with_highest_downtime_of_each_cluster_header =
		document.createElement('h5');
	top_20_servers_with_highest_downtime_of_each_cluster_header.innerText =
		'Top 20 Servers with Highest Site Downtime per Cluster';
	report_div.append(
		top_20_servers_with_highest_downtime_of_each_cluster_header,
	);

	for (const cluster of Object.keys(
		report.top_20_servers_with_highest_site_downtime_per_cluster,
	)) {
		// Sort by highest downtimes
		let data =
			report.top_20_servers_with_highest_site_downtime_per_cluster[cluster];
		if (!data || data.length === 0) continue;

		render_table_section(report_div[0], `${cluster} Cluster`, data, {
			exclude_keys: [],
			transform: data_transformer_map,
			column_header: column_header_map,
		});
	}
}

function render_problematic_site_analysis(frm, report) {
	let report_div = $('#problematic_sites_report');
	// Clean up previous report
	report_div.empty();
	report_div.css({
		display: 'flex',
		'flex-direction': 'column',
		gap: '10px',
	});

	let data = [];
	for (const [site, analysis] of Object.entries(report)) {
		data.push({
			site: site,
			...analysis,
		});
	}

	render_table_section(report_div[0], 'Problematic Sites Analysis', data, {
		exclude_keys: [],
		key_order: [
			'site',
			'status_code',
			'status',
			'proxy_server',
			'redirects',
			'error',
		],
		transform: {
			...data_transformer_map,
			redirects: (value) => (value ? value.join('\n-> ') : ''),
		},
		column_header: column_header_map,
	});
}
function render_table_section(parent_div, header_text, data, config = {}) {
	if (!data || data.length === 0) return;

	const section_div = document.createElement('div');
	section_div.style.display = 'flex';
	section_div.style.flexDirection = 'column';
	section_div.style.gap = '4px';
	section_div.style.marginBottom = '20px';

	parent_div.appendChild(section_div);

	const header = document.createElement('h5');
	header.innerText = header_text;
	section_div.appendChild(header);

	const datatable_element = document.createElement('div');
	datatable_element.style.width = '100%';
	section_div.appendChild(datatable_element);

	// Remove excluded keys
	if (config.exclude_keys) {
		data.forEach((item) => {
			config.exclude_keys.forEach((key) => delete item[key]);
		});
	}

	// Determine the key order
	let keys = Object.keys(data[0]);
	if (config.key_order) {
		// Include only keys that exist in data after exclusion
		keys = config.key_order.filter((k) => keys.includes(k));
	}

	// Transform values if needed
	const transformed_data = data.map((item) => {
		return keys.map((key) => {
			if (config.transform && config.transform[key]) {
				return config.transform[key](item[key]);
			}
			return item[key];
		});
	});

	// Prepare column headers
	const columns = keys.map(
		(key) => (config.column_header && config.column_header[key]) || key,
	);

	// Render DataTable
	new DataTable(datatable_element, {
		columns: columns,
		data: transformed_data,
	});
}

function humanize_seconds(seconds) {
	if (seconds === 0) return '0 secs';

	const units = [
		{ label: 'day', value: 86400 },
		{ label: 'hour', value: 3600 },
		{ label: 'minute', value: 60 },
		{ label: 'second', value: 1 },
	];

	for (let unit of units) {
		if (seconds >= unit.value) {
			const amount = Math.floor(seconds / unit.value);
			return `${amount} ${unit.label}${amount > 1 ? 's' : ''}`;
		}
	}
}
