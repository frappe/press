// Copyright (c) 2021, Frappe and contributors
// For license information, please see license.txt

frappe.ui.form.on('Site Creation', {
	refresh: async function(frm) {
		// TODO: check if subdomain is already taken
		await Promise.all([
			frappe.require('assets/press/js/SectionHead.js'),
			frappe.require('assets/press/js/ListComponent.js'),
			frappe.require('assets/press/js/ActionBlock.js'),
			frappe.require('assets/press/js/utils.js')
		])

		clear_block(frm, 'subdomin_block');
		new SectionHead(frm.get_field('subdomin_block').$wrapper, {
			title: 'Choose a hostname',
			description: 'Give your site a unique name. It can only contain alphanumeric characters and dashes.',
		})

		clear_block(frm, 'frappe_version_block');
		new SectionHead(frm.get_field('frappe_version_block').$wrapper, {
			title: 'Select Frappe version',
			description: 'Select the Frappe version for your site'
		})

		clear_block(frm, 'region_block');
		new SectionHead(frm.get_field('region_block').$wrapper, {
			title: 'Select Region',
			description: 'Select the datacenter region where your site should be created'
		})

		clear_block(frm, 'apps_to_install_block');
		new SectionHead(frm.get_field('apps_to_install_block').$wrapper, {
			title: 'Select apps to install',
			description: 'Choose apps to install on your site. You can select apps published on marketplace or your private apps.'
		})

		// TODO: fetch all public apps
		// TODO: show a selectable list of public apps
		clear_block(frm, 'public_apps_block');
		let public_apps = [
			{title: 'App 1', subtext: 'Subtext for app 1'},
			{title: 'App 2', subtext: 'Subtext for app 2'},
			{title: 'App 3', subtext: 'Subtext for app 3'},
			{title: 'App 4', subtext: 'Subtext for app 4'},
			{title: 'App 5', subtext: 'Subtext for app 5'},
		]
		new ListComponent(frm.get_field('public_apps_block').$wrapper, {
			data: public_apps,
			template: title_with_sub_text_and_check_checkbox
		})

		// TODO: fetch all private apps
		// TODO: show a selectable list of private apps
		clear_block(frm, 'private_apps_block');
		let private_apps = [
			{title: 'App 1', subtext: 'Subtext for app 1'},
		]
		new SectionHead(frm.get_field('private_apps_block').$wrapper, {
			description: 'Your private apps'
		})
		new ListComponent(frm.get_field('private_apps_block').$wrapper, {
			data: private_apps,
			template: title_with_sub_text_and_check_checkbox
		})

		clear_block(frm, 'restore_existing_site_block');
		new SectionHead(frm.get_field('restore_existing_site_block').$wrapper, {
			title: 'Restore an existing site',
			description: 'Restore an existing site from backup files or directly from site url.'
		})

		new SectionHead(frm.get_field('restore_using_backup_block').$wrapper, {
			description: [
				'1. Login to your site.',
				'2. From the Download Backups page, download the latest backup.',
				'3. To get files backup, click on Download Files Backup. This will generate a new files backup and you will get an email.',
				'4. Download the files backup from the links in the email and upload the files here.'
			]
		})
		new ActionBlock(frm.get_field('restore_using_backup_block').$wrapper, {
			title: 'Database Backup',
			description: 'Upload the database backup file. Usually file name ends in .sql.gz',
			button: {
				title: 'Upload',
				onclick: () => {
					frappe.msgprint(__('Upload Database Backups'));
				}
			}
		});
		new ActionBlock(frm.get_field('restore_using_backup_block').$wrapper, {
			title: 'Public Files',
			description: 'Upload the public files backup. Usually file name ends in -files.tar',
			button: {
				title: 'Upload',
				onclick: () => {
					frappe.msgprint(__('Upload Public Files'));
				}
			}
		});
		new ActionBlock(frm.get_field('restore_using_backup_block').$wrapper, {
			title: 'Private Files',
			description: 'Upload the private files backup. Usually file name ends in -private-files.tar',
			button: {
				title: 'Upload',
				onclick: () => {
					frappe.msgprint(__('Upload Private Files'));
				}
			}
		});

		new SectionHead(frm.get_field('restore_using_url_block').$wrapper, {
			description: [
				'1. Login to your site.',
				'2. From the Download Backups page, click on Download Files Backup.',
				'3. This will generate a new files backup and you will get an email.',
				'4. After that, come back here and click on Get Backups.'
			]
		})

		clear_block(frm, 'plan_section_block');
		new SectionHead(frm.get_field('plan_section_block').$wrapper, {
			title: 'Choose your plan',
			description: 'Select a plan based on the type of usage you are expecting on your site.'
		});
		// TODO: fetch all public apps
		// TODO: show a selectable list of public apps
		let plans  = [
			{title: 'Plan 1', subtext: 'Subtext for plan 1'},
			{title: 'Plan 1', subtext: 'Subtext for plan 2'},
			{title: 'Plan 1', subtext: 'Subtext for plan 3'},
			{title: 'Plan 1', subtext: 'Subtext for plan 4'},
			{title: 'Plan 1', subtext: 'Subtext for plan 5'},
		]
		new ListComponent(frm.get_field('plan_section_block').$wrapper, {
			data: plans,
			template: title_with_sub_text_and_check_checkbox
		})
	}
});
