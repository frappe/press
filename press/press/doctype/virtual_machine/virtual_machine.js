// Copyright (c) 2021, Frappe and contributors
// For license information, please see license.txt

frappe.ui.form.on('Virtual Machine', {
	refresh: function (frm) {
		[
			[__('Sync'), 'sync'],
			[__('Provision'), 'provision', true, frm.doc.status == 'Draft'],
			[__('Reboot'), 'reboot', true, frm.doc.status == 'Running'],
			[__('Stop'), 'stop', true, frm.doc.status == 'Running'],
			[__('Force Stop'), 'force_stop', true, frm.doc.status == 'Running'],
			[__('Start'), 'start', true, frm.doc.status == 'Stopped'],
			[__('Terminate'), 'terminate', true, !frm.doc.termination_protection],
			[
				__('Force Terminate'),
				'force_terminate',
				true,
				Boolean(frappe.boot.developer_mode),
			],
			[
				__('Disable Termination Protection'),
				'disable_termination_protection',
				true,
				frm.doc.termination_protection,
			],
			[
				__('Enable Termination Protection'),
				'enable_termination_protection',
				true,
				!frm.doc.termination_protection,
			],
			[__('Increase Disk Size'), 'increase_disk_size', true],
			[__('Create Image'), 'create_image', true, frm.doc.status == 'Stopped'],
			[
				__('Create Snapshots'),
				'create_snapshots',
				true,
				frm.doc.status == 'Running',
			],
			[__('Create Server'), 'create_server', true, frm.doc.series === 'f'],
			[
				__('Create Database Server'),
				'create_database_server',
				false,
				frm.doc.series === 'm',
			],
			[
				__('Create Proxy Server'),
				'create_proxy_server',
				false,
				frm.doc.series === 'n',
			],
			[
				__('Create Registry Server'),
				'create_registry_server',
				false,
				frm.doc.series === 'r',
			],
			[
				__('Create Monitor Server'),
				'create_monitor_server',
				false,
				frm.doc.series === 'm',
			],
			[
				__('Create Log Server'),
				'create_log_server',
				false,
				frm.doc.series === 'e',
			],
			[
				__('Reboot with serial console'),
				'reboot_with_serial_console',
				true,
				frm.doc.status === 'Running' && frm.doc.cloud_provider === 'AWS EC2',
			],
		].forEach(([label, method, confirm, condition]) => {
			if (typeof condition === 'undefined' || condition) {
				frm.add_custom_button(
					label,
					() => {
						if (confirm) {
							frappe.confirm(
								`Are you sure you want to ${label.toLowerCase()}?`,
								() =>
									frm.call(method).then((r) => {
										if (r.message) {
											frappe.msgprint(r.message);
										} else {
											frm.refresh();
										}
									}),
							);
						} else {
							frm.call(method).then((r) => {
								if (r.message) {
									frappe.msgprint(r.message);
								} else {
									frm.refresh();
								}
							});
						}
					},
					__('Actions'),
				);
			}
		});
		[
			[
				__('Resize'),
				'resize',
				frm.doc.status == 'Stopped' ||
					(frm.doc.cloud_provider == 'OCI' && frm.doc.status != 'Draft'),
			],
		].forEach(([label, method, condition]) => {
			if (typeof condition === 'undefined' || condition) {
				frm.add_custom_button(
					label,
					() => {
						frappe.prompt(
							{
								fieldtype: 'Data',
								label: 'Machine Type',
								fieldname: 'machine_type',
								reqd: 1,
							},
							({ machine_type }) => {
								frm
									.call(method, {
										machine_type,
									})
									.then((r) => frm.refresh());
							},
							__('Resize Virtual Machine'),
						);
					},
					__('Actions'),
				);
			}
		});
		[
			[
				__('Update EBS Performance'),
				'update_ebs_performance',
				frm.doc.cloud_provider == 'AWS EC2',
			],
		].forEach(([label, method, condition]) => {
			if (typeof condition === 'undefined' || condition) {
				frm.add_custom_button(
					label,
					() => {
						frappe.prompt(
							[
								{
									fieldtype: 'Int',
									label: 'IOPS',
									fieldname: 'iops',
									reqd: 1,
									default: frm.doc.volumes[0].iops,
								},
								{
									fieldtype: 'Int',
									label: 'Throughput (MB/s)',
									fieldname: 'throughput',
									reqd: 1,
									default: frm.doc.volumes[0].throughput,
								},
							],
							({ iops, throughput }) => {
								frm
									.call(method, {
										iops,
										throughput,
									})
									.then((r) => frm.refresh());
							},
							__('Update EBS Performance'),
						);
					},
					__('Actions'),
				);
			}
		});
		[
			[
				__('Update OCI Volume Performance'),
				'update_oci_volume_performance',
				frm.doc.cloud_provider == 'OCI',
			],
		].forEach(([label, method, condition]) => {
			if (typeof condition === 'undefined' || condition) {
				frm.add_custom_button(
					label,
					() => {
						frappe.prompt(
							[
								{
									fieldtype: 'Int',
									label: 'VPUs / GB',
									fieldname: 'vpus',
									reqd: 1,
									default:
										(frm.doc.volumes[0].iops / frm.doc.volumes[0].size - 45) /
										1.5,
								},
							],
							({ vpus }) => {
								frm
									.call(method, {
										vpus,
									})
									.then((r) => frm.refresh());
							},
							__('Update OCI Volume Performance'),
						);
					},
					__('Actions'),
				);
			}
		});
		[
			[
				__('Convert to ARM'),
				'convert_to_arm',
				frm.doc.cloud_provider == 'AWS EC2' && frm.doc.platform == 'x86_64',
			],
		].forEach(([label, method, condition]) => {
			if (typeof condition === 'undefined' || condition) {
				frm.add_custom_button(
					label,
					() => {
						frappe.prompt(
							[
								{
									fieldtype: 'Link',
									label: 'Virtual Machine Image',
									fieldname: 'virtual_machine_image',
									options: 'Virtual Machine Image',
									reqd: 1,
									get_query: function () {
										return {
											filters: {
												platform: 'arm64',
												cluster: frm.doc.cluster,
												status: 'Available',
												series: frm.doc.series,
											},
										};
									},
								},
								{
									fieldtype: 'Data',
									label: 'Machine Type',
									fieldname: 'machine_type',
									reqd: 1,
								},
							],
							({ virtual_machine_image, machine_type }) => {
								frm
									.call(method, {
										virtual_machine_image,
										machine_type,
									})
									.then((r) => frm.refresh());
							},
							__(label),
						);
					},
					__('Actions'),
				);
			}
		});
		if (frm.doc.status == 'Running') {
			frm.add_custom_button(
				'Attach New Volume',
				() => {
					frappe.prompt(
						[
							{
								fieldtype: 'Int',
								label: 'Size',
								fieldname: 'size',
								reqd: 1,
								default: 10,
							},
						],
						({ size }) => {
							frm
								.call('attach_new_volume', {
									size,
								})
								.then((r) => frm.refresh());
						},
						__('Attach New Volume'),
					);
				},
				__('Actions'),
			);
		}
		if (frm.doc.instance_id) {
			if (frm.doc.cloud_provider === 'AWS EC2') {
				frm.add_web_link(
					`https://${frm.doc.region}.console.aws.amazon.com/ec2/v2/home?region=${frm.doc.region}#InstanceDetails:instanceId=${frm.doc.instance_id}`,
					__('Visit AWS Dashboard'),
				);
			} else if (frm.doc.cloud_provider === 'OCI') {
				frm.add_web_link(
					`https://cloud.oracle.com/compute/instances/${frm.doc.instance_id}?region=${frm.doc.region}`,
					__('Visit OCI Dashboard'),
				);
			}
		}
	},
});

frappe.ui.form.on('Virtual Machine Volume', {
	detach(frm, cdt, cdn) {
		let row = frm.selected_doc;
		frappe.confirm(
			`Are you sure you want to detach volume ${row.volume_id}?`,
			() =>
				frm
					.call('detach', { volume_id: row.volume_id })
					.then((r) => frm.refresh()),
		);
	},
	increase_disk_size(frm, cdt, cdn) {
		let row = frm.selected_doc;
		frappe.prompt(
			{
				fieldtype: 'Int',
				label: 'Increment (GB)',
				fieldname: 'increment',
				reqd: 1,
			},
			({ increment }) => {
				frm
					.call('increase_disk_size', {
						volume_id: row.volume_id,
						increment,
					})
					.then((r) => frm.refresh());
			},
			__('Increase Disk Size'),
		);
	},
});
