// Copyright (c) 2021, Frappe and contributors
// For license information, please see license.txt

frappe.ui.form.on('Virtual Machine', {
	refresh: function (frm) {
		if (frm.doc.status == 'Draft' && frm.doc.cloud_provider == 'AWS EC2') {
			frm.add_custom_button(
				__('Provision'),
				() => {
					let d = new frappe.ui.Dialog({
						title: __('Provision AWS Instance'),
						fields: [
							{
								label: __('Assign Public IP?'),
								fieldname: 'assign_public_ip',
								fieldtype: 'Check',
								default: 1,
							},
						],
						primary_action_label: __('Provision'),
						primary_action(values) {
							frm
								.call({
									doc: frm.doc,
									method: 'provision',
									args: {
										assign_public_ip: values.assign_public_ip,
									},
								})
								.then((r) => {
									if (r.message) {
										frappe.msgprint(r.message);
									} else {
										frm.refresh();
									}
								});
							d.hide();
						},
					}).show();
				},
				__('Actions'),
			);
		}

		[
			[__('Sync'), 'sync', false, frm.doc.status != 'Draft'],
			[
				__('Provision'),
				'provision',
				true,
				frm.doc.status == 'Draft' && frm.doc.cloud_provider != 'AWS EC2',
			],
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
			[
				__('Create Server'),
				'create_server',
				true,
				frm.doc.series === 'f' || frm.doc.series === 'u',
			],
			[
				__('Create Database Server'),
				'create_database_server',
				false,
				frm.doc.series === 'm' || frm.doc.series === 'u',
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
				frm.doc.series === 'p',
			],
			[
				__('Create Log Server'),
				'create_log_server',
				false,
				frm.doc.series === 'e',
			],
			[
				__('Create NAT Server'),
				'create_nat_server',
				false,
				frm.doc.series === 'nat',
			],
			[
				__('Reboot with serial console'),
				'reboot_with_serial_console',
				true,
				frm.doc.status === 'Running' && frm.doc.cloud_provider === 'AWS EC2',
			],
			[
				__('Assign Secondary Private IP'),
				'assign_secondary_private_ip',
				true,
				frm.doc.status === 'Running' &&
					frm.doc.cloud_provider === 'AWS EC2' &&
					!!!frm.doc.secondary_private_ip &&
					frm.doc.series === 'nat',
			],
			[
				__('Disassociate Auto Assigned Public IP'),
				'disassociate_auto_assigned_public_ip',
				true,
				frm.doc.status === 'Running' &&
					frm.doc.cloud_provider === 'AWS EC2' &&
					!!frm.doc.public_ip_address &&
					!frm.doc.is_static_ip,
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
				let fields = [
					{
						fieldtype: 'Data',
						label: 'Machine Type',
						fieldname: 'machine_type',
						reqd: 1,
					},
				];
				if (frm.doc.cloud_provider == 'Hetzner') {
					fields.push({
						fieldtype: 'Check',
						label: 'Upgrade Disk ?',
						fieldname: 'upgrade_disk',
						default: 0,
					});
				}
				frm.add_custom_button(
					label,
					() => {
						frappe.prompt(
							fields,
							({ machine_type, upgrade_disk }) => {
								frm
									.call(method, {
										machine_type,
										upgrade_disk,
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
		if (frm.doc.platform == 'x86_64') {
			frm.add_custom_button(
				'Convert to AMD',
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
											platform: 'x86_64',
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
								.call('convert_to_amd', {
									virtual_machine_image,
									machine_type,
								})
								.then((r) => frm.refresh());
						},
						__('Convert to AMD'),
					);
				},
				__('Actions'),
			);
		}
		if (frm.doc.status == 'Running') {
			frm.add_custom_button(
				__('Attach New Volume'),
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
							{
								fieldtype: 'Int',
								label: 'IOPS',
								fieldname: 'iops',
								reqd: 1,
								default: 3000,
							},
							{
								fieldtype: 'Int',
								label: 'Throughput (MB/s)',
								fieldname: 'throughput',
								reqd: 1,
								default: 125,
							},
						],
						({ size, iops, throughput }) => {
							frm
								.call('attach_new_volume', {
									size,
									iops,
									throughput,
								})
								.then((r) => frm.refresh());
						},
						__('Attach New Volume'),
					);
				},
				__('Actions'),
			);

			frm.add_custom_button(
				'Attach Volume',
				() => {
					frappe.prompt(
						[
							{
								fieldtype: 'Data',
								label: 'Volume ID',
								fieldname: 'volume_id',
								reqd: 1,
							},
							{
								fieldtype: 'Check',
								label: 'Is Temporary Volume ?',
								fieldname: 'is_temporary_volume',
								default: 1,
							},
						],
						({ volume_id, is_temporary_volume }) => {
							frm
								.call('attach_volume', {
									volume_id,
									is_temporary_volume,
								})
								.then((r) => frm.refresh());
						},
						__('Attach Volume'),
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
	toggle_rightsize(frm, cdt, cdn) {
		frappe.model.set_value(cdt, cdn, 'skip_rightsize', !frm.selected_doc.skip_rightsize);
		frm.save();
	},
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
	delete_volume(frm, cdt, cdn) {
		let row = frm.selected_doc;
		frappe.confirm(
			`Are you sure you want to delete volume ${row.volume_id}?`,
			() =>
				frm
					.call('delete_volume', { volume_id: row.volume_id })
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
	update_ebs_performance(frm, cdt, cdn) {
		let row = frm.selected_doc;
		frappe.prompt(
			[
				{
					fieldtype: 'Int',
					label: 'IOPS',
					fieldname: 'iops',
					reqd: 1,
					default: row.iops,
				},
				{
					fieldtype: 'Int',
					label: 'Throughput (MB/s)',
					fieldname: 'throughput',
					reqd: 1,
					default: row.throughput,
				},
			],
			({ iops, throughput }) => {
				frm
					.call('update_ebs_performance', {
						volume_id: row.volume_id,
						iops,
						throughput,
					})
					.then((r) => frm.refresh());
			},
			__('Update EBS Performance'),
		);
	},
});
