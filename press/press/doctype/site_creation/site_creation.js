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
			description: 'Select a Frappe version or a Release Group for your site'
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

		load_apps(frm);

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
		let plans = await frappe.db.get_list('Plan', {
			fields: ['name']
		})
		console.log(plans);
		plans = remap(plans, (d)=> {
			return {
				title: d
			}
		})
		new SectionHead(frm.get_field('plan_section_block').$wrapper, {
			title: 'Choose your plan',
			description: 'Select a plan based on the type of usage you are expecting on your site.'
		});
		new ListComponent(frm.get_field('plan_section_block').$wrapper, {
			data: plans,
			template: title_with_sub_text_and_check_checkbox
		})
	},
	release_group: async function(frm) {
		if(frm.doc.release_group) {
			let rb = await frappe.db.get_doc('Release Group', frm.doc.release_group);
			frm.doc.public_apps = [];

			console.log(rb);
			for(let app of rb.apps) {
				if(app.app != 'frappe') frm.doc.public_apps.push(app.title);
			}

			refresh_field('public_apps');
			load_apps(frm);
		}
	},
	frappe_version: async function(frm) {
		if(frm.doc.frappe_version) {
			let rb = (await frappe.db.get_value('Release Group', {
				'default': '1',
				'public': '1',
				'version': frm.doc.frappe_version
			}, ['name'])).message;
	
			console.log(rb);
			if (Object.keys(rb).length !== 0) {
				frm.doc.public_apps = [];
				for(let app of rb.apps) {
					if(app.app != 'frappe') frm.doc.public_apps.push(app.title);
				}

				refresh_field('public_apps');
				load_apps(frm);
			} else {
				frappe.msgprint(__('There is no public Release Group for this frappe version'))
			}
		}
	},
	subdomain: async function(frm) {
		let subdomain = frm.doc.subdomain;
		if(subdomain) {
			let error = validate_subdomain(subdomain);
			if(!error) {
				let subdomain_taken = (await frappe.call({
					method: 'press.api.site.exists',
					args: {
						subdomain: subdomain
					}
				})).message;
				console.log(subdomain_taken);
				if(subdomain_taken) {
					error = `${subdomain} already exists.`;
				}
			}
			if (error) frappe.msgprint(__(error));
		}
	}
});

function load_apps(frm) {
	let public_apps = frm.doc.public_apps;
	let private_apps = frm.doc.private_apps;

	clear_block(frm, 'public_apps_block');
	if(public_apps) {
		public_apps = remap(public_apps, (d) => {
			return {
				title: d
			}
		})
		new ListComponent(frm.get_field('public_apps_block').$wrapper, {
			data: public_apps,
			template: title_with_sub_text_and_check_checkbox
		})
	}

	clear_block(frm, 'private_apps_block');
	if(private_apps) {
		private_apps = [
			{title: 'App 1', subtext: 'Subtext for app 1'},
		]
		new SectionHead(frm.get_field('private_apps_block').$wrapper, {
			description: 'Your private apps'
		})
		new ListComponent(frm.get_field('private_apps_block').$wrapper, {
			data: private_apps,
			template: title_with_sub_text_and_check_checkbox
		})
	}
}

function validate_subdomain(subdomain) {
	if (!subdomain) {
		return 'Subdomain cannot be empty';
	}
	if (subdomain.length < 5) {
		return 'Subdomain too short. Use 5 or more characters';
	}
	if (subdomain.length > 32) {
		return 'Subdomain too long. Use 32 or less characters';
	}
	if (!subdomain.match(/^[a-z0-9][a-z0-9-]*[a-z0-9]$/)) {
		return 'Subdomain contains invalid characters. Use lowercase characters, numbers and hyphens';
	}
	return null;
}