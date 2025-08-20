# API Documentation

This document lists whitelisted API methods available in the Press application. Each method can be accessed via `/api/method/<module>.<function>` in Frappe.

## `api.__init__`
- `api.__init__.handle_suspended_site_redirection` [ANY] (guest)
- `api.__init__.script` [ANY] (guest)
- `api.__init__.script_2` [ANY] (guest)

## `api.account`
- `api.account.active_servers` [ANY]
- `api.account.add_key` [ANY]
- `api.account.add_permission_group` [ANY]
- `api.account.add_permission_group_user` [ANY]
- `api.account.can_switch_to_team` [ANY]
- `api.account.country_list` [ANY] (guest)
- `api.account.create_api_secret` [ANY]
- `api.account.create_child_team` [ANY]
- `api.account.current_team` [ANY]
- `api.account.delete_team` [ANY] (guest)
- `api.account.disable_2fa` [ANY] - Disable 2FA for the user after verifying the TOTP code
- `api.account.disable_account` [ANY]
- `api.account.enable_2fa` [ANY] - Enable 2FA for the user after verifying the TOTP code
- `api.account.enable_account` [ANY]
- `api.account.feedback` [ANY] (guest)
- `api.account.fuse_list` [ANY]
- `api.account.get` [ANY]
- `api.account.get_2fa_qr_code_url` [ANY] - Get the QR code URL for 2FA provisioning
- `api.account.get_2fa_recovery_codes` [ANY] - Get the recovery codes for the user.
- `api.account.get_billing_information` [ANY]
- `api.account.get_emails` [ANY]
- `api.account.get_permission_options` [ANY] - [{'doctype': 'Site', 'name': 'ccc.frappe.cloud', title: '', 'perms': 'press.api.site.get'}, ...]
- `api.account.get_permission_roles` [ANY]
- `api.account.get_site_count` [ANY]
- `api.account.get_user_for_reset_password_key` [ANY] (guest)
- `api.account.get_user_ssh_keys` [ANY]
- `api.account.groups` [ANY]
- `api.account.guest_feature_flags` [ANY] (guest)
- `api.account.has_active_servers` [ANY]
- `api.account.has_method_permission` [ANY]
- `api.account.is_2fa_enabled` [ANY] (guest)
- `api.account.leave_team` [ANY]
- `api.account.login_using_key` [ANY] (guest)
- `api.account.mark_key_as_default` [ANY]
- `api.account.me` [ANY]
- `api.account.permission_group_users` [ANY]
- `api.account.recover_2fa` [ANY] (guest) - Recover 2FA using a recovery code.
- `api.account.remove_child_team` [ANY]
- `api.account.remove_permission_group` [ANY]
- `api.account.remove_permission_group_user` [ANY]
- `api.account.remove_team_member` [ANY]
- `api.account.request_team_deletion` [ANY]
- `api.account.resend_otp` [ANY] (guest)
- `api.account.reset_2fa_recovery_codes` [ANY] - Reset the recovery codes for the user.
- `api.account.reset_password` [ANY] (guest)
- `api.account.send_login_link` [ANY] (guest)
- `api.account.send_otp` [ANY] (guest)
- `api.account.send_reset_password_email` [ANY] (guest)
- `api.account.set_country` [ANY]
- `api.account.setup_account` [ANY] (guest)
- `api.account.signup` [ANY] (guest)
- `api.account.signup_settings` [ANY] (guest)
- `api.account.switch_team` [ANY]
- `api.account.update_billing_information` [ANY]
- `api.account.update_emails` [ANY]
- `api.account.update_feature_flags` [ANY]
- `api.account.update_permissions` [ANY]
- `api.account.update_profile` [ANY]
- `api.account.update_profile_picture` [ANY]
- `api.account.user_prompts` [ANY]
- `api.account.validate_request_key` [ANY] (guest)
- `api.account.verify_2fa` [ANY] (guest)
- `api.account.verify_otp` [ANY] (guest)
- `api.account.verify_otp_and_login` [ANY] (guest)

## `api.analytics`
- `api.analytics.binary_logs` [ANY]
- `api.analytics.daily_usage` [ANY]
- `api.analytics.deadlock_report` [ANY]
- `api.analytics.get` [ANY]
- `api.analytics.get_advanced_analytics` [ANY]
- `api.analytics.get_slow_logs_by_query` [ANY]
- `api.analytics.mariadb_add_suggested_index` [ANY]
- `api.analytics.mariadb_processlist` [ANY]
- `api.analytics.mariadb_slow_queries` [ANY]
- `api.analytics.plausible_analytics` [ANY] (guest)
- `api.analytics.request_logs` [ANY]

## `api.app`
- `api.app.new` [ANY]

## `api.bench`
- `api.bench.add_app` [ANY]
- `api.bench.add_apps` [ANY]
- `api.bench.add_region` [ANY]
- `api.bench.all` [ANY]
- `api.bench.all_apps` [ANY] - Return all apps in the marketplace that are not installed in the release group for adding new apps
- `api.bench.apply_patch` [ANY]
- `api.bench.apps` [ANY]
- `api.bench.archive` [ANY]
- `api.bench.available_regions` [ANY]
- `api.bench.bench_config` [ANY]
- `api.bench.bench_tags` [ANY]
- `api.bench.branch_list` [ANY] - Return a list of git branches available for the `app`
- `api.bench.candidate` [ANY]
- `api.bench.candidates` [ANY]
- `api.bench.certificate` [ANY]
- `api.bench.change_branch` [ANY] - Switch to `to_branch` for `app` in release group `name`
- `api.bench.confirm_bench_transfer` [ANY] (guest)
- `api.bench.create_deploy_candidate` [ANY]
- `api.bench.dependencies` [ANY]
- `api.bench.deploy` [ANY]
- `api.bench.deploy_and_update` [ANY]
- `api.bench.deploy_information` [ANY]
- `api.bench.exists` [ANY]
- `api.bench.fail_and_redeploy` [ANY]
- `api.bench.fetch_latest_app_update` [ANY]
- `api.bench.generate_certificate` [ANY]
- `api.bench.get` [ANY]
- `api.bench.get_default_apps` [ANY]
- `api.bench.get_installed_apps_in_version` [ANY]
- `api.bench.get_processes` [ANY]
- `api.bench.get_title_and_creation` [ANY]
- `api.bench.installable_apps` [ANY]
- `api.bench.jobs` [ANY]
- `api.bench.log` [ANY]
- `api.bench.logs` [ANY]
- `api.bench.new` [ANY]
- `api.bench.options` [ANY]
- `api.bench.rebuild` [ANY]
- `api.bench.recent_deploys` [ANY]
- `api.bench.regions` [ANY]
- `api.bench.remove_app` [ANY]
- `api.bench.rename` [ANY]
- `api.bench.restart` [ANY]
- `api.bench.running_jobs` [ANY]
- `api.bench.update` [ANY]
- `api.bench.update_all_sites` [ANY]
- `api.bench.update_config` [ANY]
- `api.bench.update_dependencies` [ANY]
- `api.bench.update_inplace` [ANY]
- `api.bench.versions` [ANY]

## `api.billing`
- `api.billing.after_card_add` [ANY]
- `api.billing.balances` [ANY]
- `api.billing.change_payment_mode` [ANY]
- `api.billing.create_payment_intent_for_buying_credits` [ANY]
- `api.billing.create_payment_intent_for_micro_debit` [ANY]
- `api.billing.create_payment_intent_for_partnership_fees` [ANY]
- `api.billing.create_payment_intent_for_prepaid_app` [ANY]
- `api.billing.create_razorpay_order` [ANY]
- `api.billing.details` [ANY]
- `api.billing.fetch_invoice_items` [ANY]
- `api.billing.finalize_invoices` [ANY]
- `api.billing.get_balance_credit` [ANY]
- `api.billing.get_customer_details` [ANY] - This method is called by frappe.io for creating Customer and Address
- `api.billing.get_invoice_usage` [ANY]
- `api.billing.get_latest_unpaid_invoice` [ANY]
- `api.billing.get_payment_methods` [ANY]
- `api.billing.get_publishable_key_and_setup_intent` [ANY]
- `api.billing.get_summary` [ANY]
- `api.billing.get_unpaid_invoices` [ANY]
- `api.billing.handle_razorpay_payment_failed` [ANY]
- `api.billing.handle_razorpay_payment_success` [ANY]
- `api.billing.invoices_and_payments` [ANY]
- `api.billing.past_invoices` [ANY]
- `api.billing.prepaid_credits_via_onboarding` [ANY] - When prepaid credits are bought, the balance is not immediately reflected.
- `api.billing.refresh_invoice_link` [ANY]
- `api.billing.remove_payment_method` [ANY]
- `api.billing.request_for_payment` [ANY] - request for payments
- `api.billing.set_as_default` [ANY]
- `api.billing.setup_intent_success` [ANY]
- `api.billing.total_unpaid_amount` [ANY]
- `api.billing.unpaid_invoices` [ANY]
- `api.billing.upcoming_invoice` [ANY]
- `api.billing.validate_gst` [ANY]
- `api.billing.verify_m_pesa_transaction` [ANY] (guest) - Verify the transaction result received via callback from STK.

## `api.callbacks`
- `api.callbacks.callback` [ANY] (guest) - Handle job updates sent from agent.

## `api.central`
- `api.central.account_request` [ANY] (guest)
- `api.central.check_subdomain_availability` [ANY] (guest)
- `api.central.get_trial_end_date` [ANY] (guest)
- `api.central.options_for_regional_data` [ANY] (guest)
- `api.central.send_login_link` [ANY] (guest)
- `api.central.setup_account` [ANY] (guest)

## `api.client`
- `api.client.delete` [DELETE,POST]
- `api.client.get` [ANY]
- `api.client.get_list` [ANY]
- `api.client.insert` [POST,PUT]
- `api.client.run_doc_method` [ANY]
- `api.client.search_link` [ANY]
- `api.client.set_value` [POST,PUT]

## `api.config`
- `api.config.is_valid` [ANY]
- `api.config.standard_keys` [ANY]

## `api.cookies`
- `api.cookies.update_preferences` [ANY] (guest)

## `api.dashboard`
- `api.dashboard.add_tag` [ANY]
- `api.dashboard.all` [ANY]
- `api.dashboard.create_new_tag` [ANY]
- `api.dashboard.remove_tag` [ANY]

## `api.developer.marketplace`
- `api.developer.marketplace.change_site_plan` [ANY] (guest)
- `api.developer.marketplace.get_plans` [ANY] (guest)
- `api.developer.marketplace.get_publishable_key_and_setup_intent` [ANY] (guest)
- `api.developer.marketplace.get_subscription` [ANY] (guest)
- `api.developer.marketplace.get_subscription_info` [ANY] (guest)
- `api.developer.marketplace.get_subscription_status` [ANY] (guest)
- `api.developer.marketplace.send_login_link` [ANY] (guest)
- `api.developer.marketplace.setup_intent_success` [ANY] (guest)
- `api.developer.marketplace.update_billing_info` [ANY] (guest)

## `api.developer.saas`
- `api.developer.saas.get_plan_config` [ANY] (guest)
- `api.developer.saas.get_subscription_info` [ANY] (guest)
- `api.developer.saas.get_subscription_status` [ANY] (guest)
- `api.developer.saas.get_trial_expiry` [ANY] (guest)
- `api.developer.saas.login_to_fc` [ANY] (guest)
- `api.developer.saas.ping` [ANY] (guest)
- `api.developer.saas.send_verification_code` [POST] (guest)
- `api.developer.saas.verify_verification_code` [POST] (guest)

## `api.email`
- `api.email.email_ping` [ANY] (guest)
- `api.email.event_log` [ANY] (guest) - log the webhook and forward it to site
- `api.email.get_analytics` [ANY] (guest) - send data for a specific month
- `api.email.send_mime_mail` [ANY] (guest) - send api request to mailgun

## `api.github`
- `api.github.app` [ANY]
- `api.github.branches` [ANY]
- `api.github.clear_token_and_get_installation_url` [ANY]
- `api.github.hook` [ANY] (guest)
- `api.github.options` [ANY]
- `api.github.repository` [ANY]

## `api.google`
- `api.google.callback` [ANY] (guest)
- `api.google.login` [ANY] (guest)

## `api.log_browser`
- `api.log_browser.get_log` [ANY]

## `api.marketplace`
- `api.marketplace.add_app` [ANY]
- `api.marketplace.add_app_screenshot` [ANY] - Handles App Image Upload
- `api.marketplace.add_code_review_comment` [ANY]
- `api.marketplace.add_reply` [ANY]
- `api.marketplace.add_version` [ANY]
- `api.marketplace.analytics` [ANY]
- `api.marketplace.become_publisher` [ANY] - Turn on marketplace developer mode for current team
- `api.marketplace.branches` [ANY]
- `api.marketplace.cancel_approval_request` [ANY] - Cancel Approval Request for given `app_release`
- `api.marketplace.change_app_plan` [ANY]
- `api.marketplace.change_branch` [ANY]
- `api.marketplace.communication` [ANY]
- `api.marketplace.create_app_plan` [ANY]
- `api.marketplace.create_approval_request` [ANY] - Create a new Approval Request for given `app_release`
- `api.marketplace.create_site_for_app` [ANY] - Create a site for a marketplace app
- `api.marketplace.deploy_information` [ANY] - Return the deploy information for marketplace app `app`
- `api.marketplace.fetch_readme` [ANY]
- `api.marketplace.frappe_versions` [ANY] - Return a list of Frappe Version names
- `api.marketplace.get` [ANY]
- `api.marketplace.get_app` [ANY] - Return the `Marketplace App` document with name
- `api.marketplace.get_app_info` [ANY]
- `api.marketplace.get_app_plans` [ANY]
- `api.marketplace.get_app_source` [ANY] - Return `App Source` document having `name`
- `api.marketplace.get_apps` [ANY] - Return list of apps developed by the current team
- `api.marketplace.get_apps_with_plans` [ANY]
- `api.marketplace.get_install_app_options` [ANY] - Get options for installing a marketplace app
- `api.marketplace.get_marketplace_apps` [ANY] (guest)
- `api.marketplace.get_marketplace_apps_for_onboarding` [ANY]
- `api.marketplace.get_marketplace_subscriptions_for_site` [ANY]
- `api.marketplace.get_payout_details` [ANY]
- `api.marketplace.get_payouts_list` [ANY]
- `api.marketplace.get_promotional_banners` [ANY]
- `api.marketplace.get_publisher_profile_info` [ANY]
- `api.marketplace.get_subscriptions_list` [ANY]
- `api.marketplace.latest_approved_release` [ANY] - Return the latest app release with `approved` status
- `api.marketplace.login_via_token` [ANY] (guest)
- `api.marketplace.mark_app_ready_for_review` [ANY]
- `api.marketplace.new_app` [ANY]
- `api.marketplace.options_for_marketplace_app` [ANY]
- `api.marketplace.options_for_quick_install` [ANY]
- `api.marketplace.options_for_version` [ANY]
- `api.marketplace.profile_image_url` [ANY]
- `api.marketplace.reason_for_rejection` [ANY] - Return feedback given on a `Rejected` approval request
- `api.marketplace.releases` [ANY] - Return list of App Releases for this `app` and `source` in order of creation time
- `api.marketplace.remove_app_screenshot` [ANY]
- `api.marketplace.remove_version` [ANY]
- `api.marketplace.review_steps` [ANY]
- `api.marketplace.submit_developer_reply` [ANY]
- `api.marketplace.submit_user_review` [ANY]
- `api.marketplace.subscriptions` [ANY]
- `api.marketplace.update_app_description` [ANY] - Update the `long_description` of Marketplace App `name`
- `api.marketplace.update_app_image` [ANY] - Handles App Image Upload
- `api.marketplace.update_app_links` [ANY] - Update links related to app
- `api.marketplace.update_app_plan` [ANY]
- `api.marketplace.update_app_summary` [ANY] - Update the `description` of Marketplace App `name`
- `api.marketplace.update_app_title` [ANY] - Update `title` and `category`
- `api.marketplace.update_publisher_profile` [ANY] - Update if exists, otherwise create

## `api.monitoring`
- `api.monitoring.alert` [ANY] (guest)
- `api.monitoring.targets` [ANY] (guest)

## `api.notifications`
- `api.notifications.get_notifications` [ANY]
- `api.notifications.get_unread_count` [ANY]
- `api.notifications.mark_all_notifications_as_read` [ANY]

## `api.oauth`
- `api.oauth.callback` [ANY] (guest)
- `api.oauth.google_login` [ANY] (guest)
- `api.oauth.oauth_authorize_url` [ANY] (guest)
- `api.oauth.saas_setup` [ANY] (guest)

## `api.partner`
- `api.partner.add_partner` [ANY]
- `api.partner.apply_for_certificate` [ANY]
- `api.partner.approve_partner_request` [ANY]
- `api.partner.calculate_partner_tier` [ANY]
- `api.partner.get_current_month_partner_contribution` [ANY]
- `api.partner.get_local_payment_setup` [ANY]
- `api.partner.get_partner_contribution_list` [ANY]
- `api.partner.get_partner_customers` [ANY]
- `api.partner.get_partner_details` [ANY]
- `api.partner.get_partner_members` [ANY]
- `api.partner.get_partner_name` [ANY]
- `api.partner.get_partner_request_status` [ANY]
- `api.partner.get_partner_teams` [ANY]
- `api.partner.get_prev_month_partner_contribution` [ANY]
- `api.partner.get_total_partner_contribution` [ANY]
- `api.partner.remove_partner` [ANY]
- `api.partner.transfer_credits` [ANY]
- `api.partner.update_partnership_date` [ANY]
- `api.partner.validate_partner_code` [ANY]

## `api.payment`
- `api.payment.all` [ANY]

## `api.product_trial`
- `api.product_trial.get_account_request_for_product_signup` [ANY] (guest)
- `api.product_trial.get_request` [POST]
- `api.product_trial.login_using_code` [ANY] (guest)
- `api.product_trial.send_verification_code_for_login` [ANY] (guest)
- `api.product_trial.setup_account` [POST] (guest)

## `api.regional_payments.mpesa.utils`
- `api.regional_payments.mpesa.utils.create_exchange_rate` [ANY] - Create a new exchange rate record.
- `api.regional_payments.mpesa.utils.create_invoice_partner_site` [ANY]
- `api.regional_payments.mpesa.utils.display_invoices_by_partner` [ANY] - Display the list of invoices by partner.
- `api.regional_payments.mpesa.utils.display_mpesa_payment_partners` [ANY] - Display the list of partners in the system with Mpesa integration enabled.
- `api.regional_payments.mpesa.utils.display_payment_gateway` [ANY] - Display the payment gateway for the partner.
- `api.regional_payments.mpesa.utils.display_payment_gateways` [ANY] - Display the list of payment gateways for the partner.
- `api.regional_payments.mpesa.utils.display_payment_partners` [ANY] - Display the list of partners in the system.
- `api.regional_payments.mpesa.utils.fetch_mpesa_setup` [ANY]
- `api.regional_payments.mpesa.utils.fetch_payments` [ANY]
- `api.regional_payments.mpesa.utils.fetch_payouts` [ANY]
- `api.regional_payments.mpesa.utils.fetch_percentage_commission` [ANY] - Fetch the percentage commission for the partner.
- `api.regional_payments.mpesa.utils.get_exchange_rate` [ANY] - Get the latest exchange rate for the given currencies.
- `api.regional_payments.mpesa.utils.get_gateway_controller` [ANY]
- `api.regional_payments.mpesa.utils.get_payment_gateway_details` [ANY]
- `api.regional_payments.mpesa.utils.get_tax_percentage` [ANY]
- `api.regional_payments.mpesa.utils.update_mpesa_setup` [ANY] - Create Mpesa Settings for the team.
- `api.regional_payments.mpesa.utils.update_payment_gateway_settings` [ANY] - Create Payment Gateway Settings for the team.

## `api.saas`
- `api.saas.account_request` [ANY] (guest) - return: Stripe setup intent and AR key if stripe flow, else None
- `api.saas.check_subdomain_availability` [ANY] (guest) - Checks if subdomain is available to create a new site
- `api.saas.get_saas_site_status` [ANY]
- `api.saas.get_site_status` [ANY] (guest) - return: Site status
- `api.saas.get_site_url_and_sid` [ANY] (guest) - return: Site url and session id for login-redirect
- `api.saas.headless_setup_account` [ANY] (guest) - Ignores the data collection step in setup-account.html
- `api.saas.new_saas_site` [ANY]
- `api.saas.setup_account` [ANY] (guest) - Includes the data collection step in setup-account.html

## `api.security`
- `api.security.fetch_security_updates` [ANY]
- `api.security.fetch_ssh_session_activity` [ANY]
- `api.security.fetch_ssh_session_logs` [ANY]
- `api.security.fetch_ssh_sessions` [ANY]
- `api.security.get_security_update_details` [ANY]
- `api.security.get_servers` [ANY]

## `api.selfhosted`
- `api.selfhosted.check_dns` [ANY]
- `api.selfhosted.create_and_verify_selfhosted` [ANY]
- `api.selfhosted.get_plans` [ANY]
- `api.selfhosted.new` [ANY]
- `api.selfhosted.options_for_new` [ANY]
- `api.selfhosted.setup` [ANY]
- `api.selfhosted.sshkey` [ANY]
- `api.selfhosted.verify` [ANY]

## `api.server`
- `api.server.all` [ANY]
- `api.server.analytics` [ANY]
- `api.server.archive` [ANY]
- `api.server.change_plan` [ANY]
- `api.server.get` [ANY]
- `api.server.get_request_by_site` [ANY]
- `api.server.get_slow_logs_by_site` [ANY]
- `api.server.get_title_and_cluster` [ANY]
- `api.server.groups` [ANY]
- `api.server.jobs` [ANY]
- `api.server.new` [ANY]
- `api.server.options` [ANY]
- `api.server.overview` [ANY]
- `api.server.plans` [ANY]
- `api.server.play` [ANY]
- `api.server.plays` [ANY]
- `api.server.press_jobs` [ANY]
- `api.server.reboot` [ANY]
- `api.server.rename` [ANY]
- `api.server.server_tags` [ANY]
- `api.server.usage` [ANY]

## `api.site`
- `api.site.activate` [ANY]
- `api.site.activities` [ANY]
- `api.site.add_domain` [ANY]
- `api.site.add_server_to_release_group` [ANY]
- `api.site.all` [ANY]
- `api.site.app_details_for_new_public_site` [ANY]
- `api.site.archive` [ANY]
- `api.site.available_apps` [ANY]
- `api.site.backup` [ANY]
- `api.site.backups` [ANY]
- `api.site.change_auto_update` [ANY]
- `api.site.change_group` [ANY]
- `api.site.change_group_options` [ANY]
- `api.site.change_notify_email` [ANY]
- `api.site.change_plan` [ANY]
- `api.site.change_region` [ANY]
- `api.site.change_region_options` [ANY]
- `api.site.change_server` [ANY]
- `api.site.change_server_options` [ANY]
- `api.site.check_dns` [ANY]
- `api.site.check_for_updates` [ANY]
- `api.site.clear_cache` [ANY]
- `api.site.clone_group` [ANY]
- `api.site.confirm_site_transfer` [ANY] (guest)
- `api.site.current_plan` [ANY]
- `api.site.deactivate` [ANY]
- `api.site.disable_auto_update` [ANY]
- `api.site.domain_exists` [ANY]
- `api.site.domains` [ANY]
- `api.site.enable_auto_update` [ANY]
- `api.site.exists` [ANY] (guest)
- `api.site.fetch_sites_data_for_export` [ANY]
- `api.site.get` [ANY]
- `api.site.get_auto_update_info` [ANY]
- `api.site.get_backup_link` [ANY]
- `api.site.get_backup_links` [ANY]
- `api.site.get_domain` [ANY]
- `api.site.get_job_status` [ANY]
- `api.site.get_new_site_options` [ANY]
- `api.site.get_plans` [ANY]
- `api.site.get_private_groups_for_upgrade` [ANY]
- `api.site.get_site_config_standard_keys` [ANY]
- `api.site.get_site_plans` [ANY]
- `api.site.get_trial_plan` [ANY]
- `api.site.get_upload_link` [ANY]
- `api.site.install_app` [ANY]
- `api.site.installed_apps` [ANY]
- `api.site.is_server_added_in_group` [ANY]
- `api.site.job` [ANY]
- `api.site.jobs` [ANY]
- `api.site.last_migrate_failed` [ANY]
- `api.site.log` [ANY]
- `api.site.login` [ANY]
- `api.site.logs` [ANY]
- `api.site.migrate` [ANY]
- `api.site.multipart_exit` [ANY]
- `api.site.new` [ANY]
- `api.site.options_for_new` [ANY]
- `api.site.reinstall` [ANY]
- `api.site.remove_domain` [ANY]
- `api.site.restore` [ANY]
- `api.site.retry_add_domain` [ANY]
- `api.site.running_jobs` [ANY]
- `api.site.send_change_team_request` [ANY]
- `api.site.set_host_name` [ANY]
- `api.site.set_redirect` [ANY]
- `api.site.setup_wizard_complete` [ANY]
- `api.site.site_config` [ANY]
- `api.site.site_tags` [ANY]
- `api.site.uninstall_app` [ANY]
- `api.site.unset_redirect` [ANY]
- `api.site.update` [ANY]
- `api.site.update_auto_update_info` [ANY]
- `api.site.update_config` [ANY]
- `api.site.uploaded_backup_info` [ANY]
- `api.site.validate_group_for_upgrade` [ANY]
- `api.site.validate_restoration_space_requirements` [ANY]
- `api.site.version_upgrade` [ANY]

## `api.site_backup`
- `api.site_backup.create_snapshot` [ANY] (guest) - This API will be called by agent during physical backup of database server.

## `api.site_login`
- `api.site_login.check_session_id` [ANY] (guest) - Check if the session id is valid
- `api.site_login.get_product_sites_of_user` [ANY] (guest) - Get all product sites of a user
- `api.site_login.login_to_site` [ANY] (guest) - Login to the product site
- `api.site_login.send_otp` [ANY] (guest) - Send OTP to the user trying to login to the product site from /site-login page
- `api.site_login.sync_product_site_user` [POST] (guest) - Sync user info from product site
- `api.site_login.verify_otp` [ANY] (guest) - Verify OTP

## `api.spaces`
- `api.spaces.code_server` [ANY]
- `api.spaces.code_server_bench_options` [ANY]
- `api.spaces.code_server_domain` [ANY] - Returns the domain for code servers
- `api.spaces.code_server_group_options` [ANY]
- `api.spaces.code_server_jobs` [ANY]
- `api.spaces.code_server_password` [ANY]
- `api.spaces.create_code_server` [ANY] - Create a new code server doc
- `api.spaces.drop_code_server` [ANY]
- `api.spaces.exists` [ANY] - Checks if a subdomain is already taken
- `api.spaces.spaces` [ANY] - Returns all spaces and code servers for the current team
- `api.spaces.start_code_server` [ANY]
- `api.spaces.stop_code_server` [ANY]

## `api.telegram`
- `api.telegram.hook` [ANY] (guest)

## `api.webhook`
- `api.webhook.add` [ANY]
- `api.webhook.attempt` [ANY]
- `api.webhook.attempts` [ANY]
- `api.webhook.available_events` [ANY] (guest)
- `api.webhook.update` [ANY]

## `experimental.doctype.referral_bonus.referral_bonus`
- `experimental.doctype.referral_bonus.referral_bonus.allocate_credits` [ANY]

## `infrastructure.doctype.arm_build_record.arm_build_record`
- `infrastructure.doctype.arm_build_record.arm_build_record.cancel_all_jobs` [ANY] - Cancel all current running jobs
- `infrastructure.doctype.arm_build_record.arm_build_record.pull_images` [ANY] - Pull images on app server using image tags
- `infrastructure.doctype.arm_build_record.arm_build_record.remove_build_from_deploy_candidate` [ANY] - Remove arm build field from deploy candidate.
- `infrastructure.doctype.arm_build_record.arm_build_record.retry` [ANY]
- `infrastructure.doctype.arm_build_record.arm_build_record.sync_status` [ANY]
- `infrastructure.doctype.arm_build_record.arm_build_record.update_image_tags_on_benches` [ANY] - This step replaces the image tags on the app server itself.

## `infrastructure.doctype.ssh_access_audit.ssh_access_audit`
- `infrastructure.doctype.ssh_access_audit.ssh_access_audit.run` [ANY]

## `infrastructure.doctype.virtual_disk_resize.virtual_disk_resize`
- `infrastructure.doctype.virtual_disk_resize.virtual_disk_resize.execute` [ANY]
- `infrastructure.doctype.virtual_disk_resize.virtual_disk_resize.execute_step` [ANY]
- `infrastructure.doctype.virtual_disk_resize.virtual_disk_resize.force_continue` [ANY]
- `infrastructure.doctype.virtual_disk_resize.virtual_disk_resize.force_fail` [ANY]
- `infrastructure.doctype.virtual_disk_resize.virtual_disk_resize.next` [ANY]

## `infrastructure.doctype.virtual_machine_migration.virtual_machine_migration`
- `infrastructure.doctype.virtual_machine_migration.virtual_machine_migration.execute` [ANY]
- `infrastructure.doctype.virtual_machine_migration.virtual_machine_migration.execute_step` [ANY]
- `infrastructure.doctype.virtual_machine_migration.virtual_machine_migration.force_continue` [ANY]
- `infrastructure.doctype.virtual_machine_migration.virtual_machine_migration.force_fail` [ANY]
- `infrastructure.doctype.virtual_machine_migration.virtual_machine_migration.next` [ANY]

## `infrastructure.doctype.virtual_machine_replacement.virtual_machine_replacement`
- `infrastructure.doctype.virtual_machine_replacement.virtual_machine_replacement.execute` [ANY]
- `infrastructure.doctype.virtual_machine_replacement.virtual_machine_replacement.execute_step` [ANY]
- `infrastructure.doctype.virtual_machine_replacement.virtual_machine_replacement.force_continue` [ANY]
- `infrastructure.doctype.virtual_machine_replacement.virtual_machine_replacement.force_fail` [ANY]
- `infrastructure.doctype.virtual_machine_replacement.virtual_machine_replacement.next` [ANY]

## `marketplace.doctype.marketplace_app_subscription.marketplace_app_subscription`
- `marketplace.doctype.marketplace_app_subscription.marketplace_app_subscription.activate` [ANY]

## `overrides`
- `overrides.upload_file` [ANY] (guest)

## `press.doctype.account_request.account_request`
- `press.doctype.account_request.account_request.send_verification_email` [ANY]

## `press.doctype.add_on_settings.add_on_settings`
- `press.doctype.add_on_settings.add_on_settings.init_etcd_data` [ANY]

## `press.doctype.agent_job.agent_job`
- `press.doctype.agent_job.agent_job.cancel_job` [ANY]
- `press.doctype.agent_job.agent_job.fail_and_process_job_updates` [ANY]
- `press.doctype.agent_job.agent_job.get_status` [ANY]
- `press.doctype.agent_job.agent_job.process_job_updates` [ANY]
- `press.doctype.agent_job.agent_job.retry` [ANY]
- `press.doctype.agent_job.agent_job.retry_in_place` [ANY]
- `press.doctype.agent_job.agent_job.retry_skip_failing_patches` [ANY]
- `press.doctype.agent_job.agent_job.succeed_and_process_job_updates` [ANY]

## `press.doctype.agent_update.agent_update`
- `press.doctype.agent_update.agent_update.create_execution_plan` [ANY]
- `press.doctype.agent_update.agent_update.execute` [ANY]
- `press.doctype.agent_update.agent_update.pause` [ANY]
- `press.doctype.agent_update.agent_update.split_updates` [ANY]

## `press.doctype.analytics_server.analytics_server`
- `press.doctype.analytics_server.analytics_server.show_plausible_password` [ANY]

## `press.doctype.ansible_console.ansible_console`
- `press.doctype.ansible_console.ansible_console.execute_command` [ANY]

## `press.doctype.app_patch.app_patch`
- `press.doctype.app_patch.app_patch.delete_patch` [ANY]
- `press.doctype.app_patch.app_patch.revert_all_patches` [ANY]

## `press.doctype.app_release.app_release`
- `press.doctype.app_release.app_release.cleanup` [ANY]
- `press.doctype.app_release.app_release.clone` [ANY]

## `press.doctype.app_release_approval_request.app_release_approval_request`
- `press.doctype.app_release_approval_request.app_release_approval_request.start_screening` [ANY]

## `press.doctype.app_source.app_source`
- `press.doctype.app_source.app_source.create_release` [ANY]

## `press.doctype.bench.bench`
- `press.doctype.bench.bench.add_ssh_user` [ANY]
- `press.doctype.bench.bench.force_update_limits` [ANY]
- `press.doctype.bench.bench.generate_nginx_config` [ANY]
- `press.doctype.bench.bench.move_sites` [ANY]
- `press.doctype.bench.bench.remove_ssh_user` [ANY]
- `press.doctype.bench.bench.retry_bench` [ANY]
- `press.doctype.bench.bench.sync_analytics` [ANY]
- `press.doctype.bench.bench.sync_info` [ANY] - Initiates a Job to update Site Usage, site.config.encryption_key and timezone details for all sites on Bench.

## `press.doctype.bench_shell.bench_shell`
- `press.doctype.bench_shell.bench_shell.run_command` [ANY]

## `press.doctype.build_cache_shell.build_cache_shell`
- `press.doctype.build_cache_shell.build_cache_shell.run_command` [ANY]

## `press.doctype.cluster.cluster`
- `press.doctype.cluster.cluster.add_images` [ANY]
- `press.doctype.cluster.cluster.create_servers` [ANY] - Creates servers for the cluster

## `press.doctype.code_server.code_server`
- `press.doctype.code_server.code_server.archive` [ANY]
- `press.doctype.code_server.code_server.setup` [ANY]
- `press.doctype.code_server.code_server.start` [ANY]
- `press.doctype.code_server.code_server.stop` [ANY]

## `press.doctype.database_server.database_server`
- `press.doctype.database_server.database_server.adjust_memory_config` [ANY]
- `press.doctype.database_server.database_server.convert_from_frappe_server` [ANY]
- `press.doctype.database_server.database_server.fetch_stalks` [ANY]
- `press.doctype.database_server.database_server.get_binlog_summary` [ANY]
- `press.doctype.database_server.database_server.perform_physical_backup` [ANY]
- `press.doctype.database_server.database_server.purge_binlogs` [ANY]
- `press.doctype.database_server.database_server.reconfigure_mariadb_exporter` [ANY]
- `press.doctype.database_server.database_server.reset_root_password` [ANY]
- `press.doctype.database_server.database_server.restart_mariadb` [ANY]
- `press.doctype.database_server.database_server.run_upgrade_mariadb_job` [ANY]
- `press.doctype.database_server.database_server.setup_deadlock_logger` [ANY]
- `press.doctype.database_server.database_server.setup_essentials` [ANY] - Setup missing essentials after server setup
- `press.doctype.database_server.database_server.setup_logrotate` [ANY]
- `press.doctype.database_server.database_server.setup_mariadb_debug_symbols` [ANY]
- `press.doctype.database_server.database_server.setup_pt_stalk` [ANY]
- `press.doctype.database_server.database_server.setup_replication` [ANY]
- `press.doctype.database_server.database_server.stop_mariadb` [ANY]
- `press.doctype.database_server.database_server.sync_binlogs_info` [ANY]
- `press.doctype.database_server.database_server.trigger_failover` [ANY]
- `press.doctype.database_server.database_server.update_mariadb` [ANY]
- `press.doctype.database_server.database_server.update_memory_allocator` [ANY]
- `press.doctype.database_server.database_server.upgrade_mariadb` [ANY]
- `press.doctype.database_server.database_server.upgrade_mariadb_patched` [ANY]

## `press.doctype.deploy_candidate.deploy_candidate`
- `press.doctype.deploy_candidate.deploy_candidate.build` [ANY]
- `press.doctype.deploy_candidate.deploy_candidate.desk_app` [ANY]
- `press.doctype.deploy_candidate.deploy_candidate.schedule_build_and_deploy` [ANY]
- `press.doctype.deploy_candidate.deploy_candidate.toggle_builds` [ANY]

## `press.doctype.deploy_candidate_build.deploy_candidate_build`
- `press.doctype.deploy_candidate_build.deploy_candidate_build.cleanup_build_directory` [ANY]
- `press.doctype.deploy_candidate_build.deploy_candidate_build.deploy` [ANY]
- `press.doctype.deploy_candidate_build.deploy_candidate_build.fail_and_redeploy` [ANY]
- `press.doctype.deploy_candidate_build.deploy_candidate_build.fail_remote_job` [ANY]
- `press.doctype.deploy_candidate_build.deploy_candidate_build.redeploy` [ANY]
- `press.doctype.deploy_candidate_build.deploy_candidate_build.stop_and_fail` [ANY]

## `press.doctype.drip_email.drip_email`
- `press.doctype.drip_email.drip_email.send_test_email` [ANY] - Send test email to the given email address.
- `press.doctype.drip_email.drip_email.unsubscribe` [ANY] (guest) - Unsubscribe from drip emails of a site.

## `press.doctype.incident.incident`
- `press.doctype.incident.incident.cancel_stuck_jobs` [ANY] - During db reboot/upgrade some jobs tend to get stuck. This is a hack to cancel those jobs
- `press.doctype.incident.incident.get_down_site` [ANY]
- `press.doctype.incident.incident.ignore_for_server` [ANY] - Ignore incidents on server (Don't call)
- `press.doctype.incident.incident.reboot_database_server` [ANY]
- `press.doctype.incident.incident.regather_info_and_screenshots` [ANY]
- `press.doctype.incident.incident.restart_down_benches` [ANY] - Restart all benches on the server that are down

## `press.doctype.inspect_trace_id.inspect_trace_id`
- `press.doctype.inspect_trace_id.inspect_trace_id.fetch` [ANY]

## `press.doctype.invoice.invoice`
- `press.doctype.invoice.invoice.change_stripe_invoice_status` [ANY]
- `press.doctype.invoice.invoice.create_invoice_on_frappeio` [ANY]
- `press.doctype.invoice.invoice.fetch_invoice_pdf` [ANY]
- `press.doctype.invoice.invoice.fetch_mpesa_invoice_pdf` [ANY]
- `press.doctype.invoice.invoice.finalize_invoice` [ANY]
- `press.doctype.invoice.invoice.finalize_stripe_invoice` [ANY]
- `press.doctype.invoice.invoice.refresh_stripe_payment_link` [ANY]
- `press.doctype.invoice.invoice.refund` [ANY]

## `press.doctype.log_server.log_server`
- `press.doctype.log_server.log_server.install_elasticsearch_exporter` [ANY]
- `press.doctype.log_server.log_server.show_kibana_password` [ANY]

## `press.doctype.malware_scan.malware_scan`
- `press.doctype.malware_scan.malware_scan.start` [ANY]

## `press.doctype.managed_database_service.managed_database_service`
- `press.doctype.managed_database_service.managed_database_service.show_root_password` [ANY]

## `press.doctype.mariadb_binlog.mariadb_binlog`
- `press.doctype.mariadb_binlog.mariadb_binlog.download_binlog` [ANY]

## `press.doctype.mariadb_variable.mariadb_variable`
- `press.doctype.mariadb_variable.mariadb_variable.set_on_all_servers` [ANY]

## `press.doctype.monitor_server.monitor_server`
- `press.doctype.monitor_server.monitor_server.reconfigure_monitor_server` [ANY]
- `press.doctype.monitor_server.monitor_server.show_grafana_password` [ANY]

## `press.doctype.partner_payment_payout.partner_payment_payout`
- `press.doctype.partner_payment_payout.partner_payment_payout.submit_payment_payout` [ANY]

## `press.doctype.payout_order.payout_order`
- `press.doctype.payout_order.payout_order.create_payout_order_from_invoice_items` [ANY]

## `press.doctype.physical_backup_group.physical_backup_group`
- `press.doctype.physical_backup_group.physical_backup_group.activate_all_sites` [ANY]
- `press.doctype.physical_backup_group.physical_backup_group.create_duplicate_group` [ANY]
- `press.doctype.physical_backup_group.physical_backup_group.delete_backups` [ANY]
- `press.doctype.physical_backup_group.physical_backup_group.retry_failed_backups` [ANY]
- `press.doctype.physical_backup_group.physical_backup_group.set_db_sizes` [ANY]
- `press.doctype.physical_backup_group.physical_backup_group.sync` [ANY]
- `press.doctype.physical_backup_group.physical_backup_group.trigger_next_backup` [ANY]

## `press.doctype.physical_backup_restoration.physical_backup_restoration`
- `press.doctype.physical_backup_restoration.physical_backup_restoration.cleanup` [ANY]
- `press.doctype.physical_backup_restoration.physical_backup_restoration.execute` [ANY]
- `press.doctype.physical_backup_restoration.physical_backup_restoration.execute_step` [ANY]
- `press.doctype.physical_backup_restoration.physical_backup_restoration.force_continue` [ANY]
- `press.doctype.physical_backup_restoration.physical_backup_restoration.force_fail` [ANY]
- `press.doctype.physical_backup_restoration.physical_backup_restoration.next` [ANY]
- `press.doctype.physical_backup_restoration.physical_backup_restoration.retry` [ANY] (guest)

## `press.doctype.physical_restoration_test.physical_restoration_test`
- `press.doctype.physical_restoration_test.physical_restoration_test.reset_failed_restorations` [ANY]
- `press.doctype.physical_restoration_test.physical_restoration_test.start` [ANY]
- `press.doctype.physical_restoration_test.physical_restoration_test.sync` [ANY]

## `press.doctype.press_job.press_job`
- `press.doctype.press_job.press_job.force_continue` [ANY]
- `press.doctype.press_job.press_job.force_fail` [ANY]
- `press.doctype.press_job.press_job.next` [ANY]

## `press.doctype.press_job_step.press_job_step`
- `press.doctype.press_job_step.press_job_step.execute` [ANY]

## `press.doctype.press_settings.press_settings`
- `press.doctype.press_settings.press_settings.create_stripe_webhook` [ANY]
- `press.doctype.press_settings.press_settings.get_github_app_manifest` [ANY]

## `press.doctype.proxy_server.proxy_server`
- `press.doctype.proxy_server.proxy_server.reload_wireguard` [ANY]
- `press.doctype.proxy_server.proxy_server.setup_fail2ban` [ANY]
- `press.doctype.proxy_server.proxy_server.setup_proxysql` [ANY]
- `press.doctype.proxy_server.proxy_server.setup_proxysql_monitor` [ANY]
- `press.doctype.proxy_server.proxy_server.setup_replication` [ANY]
- `press.doctype.proxy_server.proxy_server.setup_ssh_proxy` [ANY]
- `press.doctype.proxy_server.proxy_server.setup_wildcard_hosts` [ANY]
- `press.doctype.proxy_server.proxy_server.setup_wireguard` [ANY]
- `press.doctype.proxy_server.proxy_server.trigger_failover` [ANY]

## `press.doctype.razorpay_payment_record.razorpay_payment_record`
- `press.doctype.razorpay_payment_record.razorpay_payment_record.sync` [ANY]

## `press.doctype.razorpay_webhook_log.razorpay_webhook_log`
- `press.doctype.razorpay_webhook_log.razorpay_webhook_log.razorpay_authorized_payment_handler` [ANY] (guest)
- `press.doctype.razorpay_webhook_log.razorpay_webhook_log.razorpay_webhook_handler` [ANY] (guest)

## `press.doctype.release_group.release_group`
- `press.doctype.release_group.release_group.add_server` [ANY]
- `press.doctype.release_group.release_group.archive` [ANY]
- `press.doctype.release_group.release_group.change_server` [ANY] - Create latest candidate in given server and tries to move sites there.
- `press.doctype.release_group.release_group.create_deploy_candidate` [ANY]
- `press.doctype.release_group.release_group.create_duplicate_deploy_candidate` [ANY]
- `press.doctype.release_group.release_group.deploy_information` [ANY]
- `press.doctype.release_group.release_group.update_benches_config` [ANY] - Update benches config for all benches in the release group

## `press.doctype.remote_file.remote_file`
- `press.doctype.remote_file.remote_file.delete_remote_object` [ANY]
- `press.doctype.remote_file.remote_file.exists` [ANY]
- `press.doctype.remote_file.remote_file.get_download_link` [ANY]

## `press.doctype.security_update_check.security_update_check`
- `press.doctype.security_update_check.security_update_check.start` [ANY]

## `press.doctype.self_hosted_server.self_hosted_server`
- `press.doctype.self_hosted_server.self_hosted_server.create_application_server` [ANY] - Add a new record to the Server doctype
- `press.doctype.self_hosted_server.self_hosted_server.create_database_server` [ANY]
- `press.doctype.self_hosted_server.self_hosted_server.create_new_rg` [ANY] - Create **a** Release Group for the apps in the Existing bench
- `press.doctype.self_hosted_server.self_hosted_server.create_new_sites` [ANY] - Create new FC sites from sites in Current Bench
- `press.doctype.self_hosted_server.self_hosted_server.create_proxy_server` [ANY] - Add a new record to the Proxy Server doctype
- `press.doctype.self_hosted_server.self_hosted_server.create_tls_certs` [ANY]
- `press.doctype.self_hosted_server.self_hosted_server.fetch_apps_and_sites` [ANY]
- `press.doctype.self_hosted_server.self_hosted_server.fetch_private_ip` [ANY] - Fetch the Private IP from the Ping Ansible Play
- `press.doctype.self_hosted_server.self_hosted_server.fetch_system_ram` [ANY] - Fetch the RAM from the Ping Ansible Play
- `press.doctype.self_hosted_server.self_hosted_server.fetch_system_specifications` [ANY] - Fetch the RAM from the Ping Ansible Play
- `press.doctype.self_hosted_server.self_hosted_server.ping_ansible` [ANY]
- `press.doctype.self_hosted_server.self_hosted_server.restore_files` [ANY]
- `press.doctype.self_hosted_server.self_hosted_server.update_tls` [ANY]

## `press.doctype.serial_console_log.serial_console_log`
- `press.doctype.serial_console_log.serial_console_log.run_sysrq` [ANY]
- `press.doctype.serial_console_log.serial_console_log.run_sysrq` [ANY]

## `press.doctype.server.server`
- `press.doctype.server.server.add_upstream_to_proxy` [ANY]
- `press.doctype.server.server.agent_set_proxy_ip` [ANY]
- `press.doctype.server.server.archive` [ANY]
- `press.doctype.server.server.auto_scale_workers` [ANY]
- `press.doctype.server.server.cleanup_unused_files` [ANY]
- `press.doctype.server.server.collect_arm_images` [ANY] - Collect arm build images of all active benches on VM
- `press.doctype.server.server.configure_ssh_logging` [ANY]
- `press.doctype.server.server.create_image` [ANY]
- `press.doctype.server.server.disable_server_for_new_benches_and_site` [ANY]
- `press.doctype.server.server.enable_server_for_new_benches_and_site` [ANY]
- `press.doctype.server.server.extend_ec2_volume` [ANY]
- `press.doctype.server.server.fetch_keys` [ANY]
- `press.doctype.server.server.fetch_security_updates` [ANY]
- `press.doctype.server.server.increase_disk_size` [ANY]
- `press.doctype.server.server.increase_swap` [ANY]
- `press.doctype.server.server.install_exporters` [ANY]
- `press.doctype.server.server.install_filebeat` [ANY]
- `press.doctype.server.server.install_nginx` [ANY]
- `press.doctype.server.server.mount_volumes` [ANY]
- `press.doctype.server.server.ping_agent` [ANY]
- `press.doctype.server.server.ping_agent_job` [ANY]
- `press.doctype.server.server.ping_ansible` [ANY]
- `press.doctype.server.server.ping_ansible_unprepared` [ANY]
- `press.doctype.server.server.prepare_server` [ANY]
- `press.doctype.server.server.reboot_with_serial_console` [ANY]
- `press.doctype.server.server.reload_nginx` [ANY]
- `press.doctype.server.server.rename_server` [ANY]
- `press.doctype.server.server.reset_sites_usage` [ANY]
- `press.doctype.server.server.reset_swap` [ANY] - Replace existing swap files with new swap file of given size
- `press.doctype.server.server.set_additional_config` [ANY] - Corresponds to Set additional config step in Create Server Press Job
- `press.doctype.server.server.set_swappiness` [ANY]
- `press.doctype.server.server.setup_agent_sentry` [ANY]
- `press.doctype.server.server.setup_fail2ban` [ANY]
- `press.doctype.server.server.setup_mysqldump` [ANY]
- `press.doctype.server.server.setup_pyspy` [ANY]
- `press.doctype.server.server.setup_replication` [ANY]
- `press.doctype.server.server.setup_server` [ANY]
- `press.doctype.server.server.setup_standalone` [ANY]
- `press.doctype.server.server.show_agent_password` [ANY]
- `press.doctype.server.server.show_agent_version` [ANY]
- `press.doctype.server.server.start_active_benches` [ANY]
- `press.doctype.server.server.update_agent` [ANY]
- `press.doctype.server.server.update_agent_ansible` [ANY]
- `press.doctype.server.server.update_tls_certificate` [ANY]
- `press.doctype.server.server.whitelist_ipaddress` [ANY]

## `press.doctype.silenced_alert.silenced_alert`
- `press.doctype.silenced_alert.silenced_alert.create_new_silence` [ANY]
- `press.doctype.silenced_alert.silenced_alert.preview_alerts` [ANY]

## `press.doctype.site.site`
- `press.doctype.site.site.backup` [ANY]
- `press.doctype.site.site.cleanup_after_archive` [ANY]
- `press.doctype.site.site.create_dns_record` [ANY]
- `press.doctype.site.site.fetch_bench_from_agent` [ANY]
- `press.doctype.site.site.forcefully_remove_site` [ANY] - Bypass all agent/press callbacks and just remove this site from the target bench/server
- `press.doctype.site.site.get_actions` [ANY]
- `press.doctype.site.site.last_migrate_failed` [ANY] - Returns `True` if the last site update's(`Migrate` deploy type) migrate site job step failed, `False` otherwise
- `press.doctype.site.site.login` [ANY]
- `press.doctype.site.site.move_to_bench` [ANY]
- `press.doctype.site.site.move_to_group` [ANY]
- `press.doctype.site.site.options_for_new` [ANY]
- `press.doctype.site.site.physical_backup` [ANY]
- `press.doctype.site.site.reset_site_usage` [ANY]
- `press.doctype.site.site.restore_tables` [ANY]
- `press.doctype.site.site.retry_archive` [ANY] - Retry archive with subdomain+domain name of site
- `press.doctype.site.site.retry_rename` [ANY] - Retry rename with current subdomain
- `press.doctype.site.site.run_after_migrate_steps` [ANY]
- `press.doctype.site.site.set_status_based_on_ping` [ANY]
- `press.doctype.site.site.show_admin_password` [ANY]
- `press.doctype.site.site.suspend` [ANY]
- `press.doctype.site.site.sync_apps` [ANY]
- `press.doctype.site.site.sync_info` [ANY] - Updates Site Usage, site.config and timezone details for site.
- `press.doctype.site.site.unsuspend` [ANY]
- `press.doctype.site.site.update_dns_record` [ANY]
- `press.doctype.site.site.update_site_config` [ANY] - Updates site.configuration, site.config and runs site.save which initiates an Agent Request
- `press.doctype.site.site.update_without_backup` [ANY]

## `press.doctype.site_database_user.site_database_user`
- `press.doctype.site_database_user.site_database_user.add_user_to_proxysql` [ANY]
- `press.doctype.site_database_user.site_database_user.apply_changes` [ANY]
- `press.doctype.site_database_user.site_database_user.create_user` [ANY]
- `press.doctype.site_database_user.site_database_user.modify_permissions` [ANY]
- `press.doctype.site_database_user.site_database_user.remove_user` [ANY]
- `press.doctype.site_database_user.site_database_user.remove_user_from_proxysql` [ANY]

## `press.doctype.site_domain.site_domain`
- `press.doctype.site_domain.site_domain.create_dns_record` [ANY]

## `press.doctype.site_migration.site_migration`
- `press.doctype.site_migration.site_migration.cleanup_and_fail` [ANY]
- `press.doctype.site_migration.site_migration.continue_from_next_pending` [ANY]
- `press.doctype.site_migration.site_migration.run_next_step` [ANY]
- `press.doctype.site_migration.site_migration.start` [ANY]

## `press.doctype.site_update.site_update`
- `press.doctype.site_update.site_update.set_cause_of_failure_is_resolved` [ANY]
- `press.doctype.site_update.site_update.set_status` [ANY]
- `press.doctype.site_update.site_update.sites_with_available_update` [ANY]
- `press.doctype.site_update.site_update.trigger_recovery_job` [ANY]

## `press.doctype.ssh_certificate_authority.ssh_certificate_authority`
- `press.doctype.ssh_certificate_authority.ssh_certificate_authority.build_image` [ANY]

## `press.doctype.storage_integration_subscription.storage_integration_subscription`
- `press.doctype.storage_integration_subscription.storage_integration_subscription.get_analytics` [ANY] (guest)
- `press.doctype.storage_integration_subscription.storage_integration_subscription.toggle_user_status` [ANY]

## `press.doctype.stripe_micro_charge_record.stripe_micro_charge_record`
- `press.doctype.stripe_micro_charge_record.stripe_micro_charge_record.refund` [ANY]

## `press.doctype.stripe_webhook_log.stripe_webhook_log`
- `press.doctype.stripe_webhook_log.stripe_webhook_log.stripe_webhook_handler` [ANY] (guest)

## `press.doctype.subscription.subscription`
- `press.doctype.subscription.subscription.create_usage_record` [ANY]

## `press.doctype.team.team`
- `press.doctype.team.team.disable_erpnext_partner_privileges` [ANY]
- `press.doctype.team.team.enable_erpnext_partner_privileges` [ANY]
- `press.doctype.team.team.get_balance` [ANY]
- `press.doctype.team.team.get_home_data` [ANY]
- `press.doctype.team.team.impersonate` [ANY]
- `press.doctype.team.team.send_email_for_failed_payment` [ANY]
- `press.doctype.team.team.send_telegram_alert_for_failed_payment` [ANY]
- `press.doctype.team.team.suspend_sites` [ANY]
- `press.doctype.team.team.unsuspend_sites` [ANY]
- `press.doctype.team.team.update_billing_details` [ANY]

## `press.doctype.tls_certificate.tls_certificate`
- `press.doctype.tls_certificate.tls_certificate._obtain_certificate` [ANY]
- `press.doctype.tls_certificate.tls_certificate.obtain_certificate` [ANY]
- `press.doctype.tls_certificate.tls_certificate.trigger_server_tls_setup_callback` [ANY]
- `press.doctype.tls_certificate.tls_certificate.trigger_site_domain_callback` [ANY]

## `press.doctype.trace_server.trace_server`
- `press.doctype.trace_server.trace_server.show_sentry_password` [ANY]
- `press.doctype.trace_server.trace_server.upgrade_server` [ANY]

## `press.doctype.user_ssh_certificate.user_ssh_certificate`
- `press.doctype.user_ssh_certificate.user_ssh_certificate.read_certificate` [ANY]

## `press.doctype.version_upgrade.version_upgrade`
- `press.doctype.version_upgrade.version_upgrade.start` [ANY]

## `press.doctype.virtual_disk_snapshot.virtual_disk_snapshot`
- `press.doctype.virtual_disk_snapshot.virtual_disk_snapshot.delete_snapshot` [ANY]
- `press.doctype.virtual_disk_snapshot.virtual_disk_snapshot.sync` [ANY]

## `press.doctype.virtual_machine.virtual_machine`
- `press.doctype.virtual_machine.virtual_machine.attach_new_volume` [ANY]
- `press.doctype.virtual_machine.virtual_machine.convert_to_amd` [ANY]
- `press.doctype.virtual_machine.virtual_machine.convert_to_arm` [ANY]
- `press.doctype.virtual_machine.virtual_machine.create_database_server` [ANY]
- `press.doctype.virtual_machine.virtual_machine.create_image` [ANY]
- `press.doctype.virtual_machine.virtual_machine.create_log_server` [ANY]
- `press.doctype.virtual_machine.virtual_machine.create_monitor_server` [ANY]
- `press.doctype.virtual_machine.virtual_machine.create_proxy_server` [ANY]
- `press.doctype.virtual_machine.virtual_machine.create_registry_server` [ANY]
- `press.doctype.virtual_machine.virtual_machine.create_server` [ANY]
- `press.doctype.virtual_machine.virtual_machine.create_snapshots` [ANY] - exclude_boot_volume is applicable only for Servers with data volume
- `press.doctype.virtual_machine.virtual_machine.delete_volume` [ANY]
- `press.doctype.virtual_machine.virtual_machine.detach` [ANY]
- `press.doctype.virtual_machine.virtual_machine.disable_termination_protection` [ANY]
- `press.doctype.virtual_machine.virtual_machine.enable_termination_protection` [ANY]
- `press.doctype.virtual_machine.virtual_machine.force_stop` [ANY]
- `press.doctype.virtual_machine.virtual_machine.force_terminate` [ANY]
- `press.doctype.virtual_machine.virtual_machine.get_ebs_performance` [ANY]
- `press.doctype.virtual_machine.virtual_machine.get_oci_volume_performance` [ANY]
- `press.doctype.virtual_machine.virtual_machine.get_serial_console_credentials` [ANY]
- `press.doctype.virtual_machine.virtual_machine.increase_disk_size` [ANY]
- `press.doctype.virtual_machine.virtual_machine.provision` [ANY]
- `press.doctype.virtual_machine.virtual_machine.reboot` [ANY]
- `press.doctype.virtual_machine.virtual_machine.reboot_with_serial_console` [ANY]
- `press.doctype.virtual_machine.virtual_machine.resize` [ANY]
- `press.doctype.virtual_machine.virtual_machine.start` [ANY]
- `press.doctype.virtual_machine.virtual_machine.stop` [ANY]
- `press.doctype.virtual_machine.virtual_machine.sync` [ANY]
- `press.doctype.virtual_machine.virtual_machine.sync_virtual_machines` [ANY]
- `press.doctype.virtual_machine.virtual_machine.terminate` [ANY]
- `press.doctype.virtual_machine.virtual_machine.update_ebs_performance` [ANY]
- `press.doctype.virtual_machine.virtual_machine.update_oci_volume_performance` [ANY]

## `press.doctype.virtual_machine_image.virtual_machine_image`
- `press.doctype.virtual_machine_image.virtual_machine_image.copy_image` [ANY]
- `press.doctype.virtual_machine_image.virtual_machine_image.delete_image` [ANY]
- `press.doctype.virtual_machine_image.virtual_machine_image.sync` [ANY]

## `press.doctype.wireguard_peer.wireguard_peer`
- `press.doctype.wireguard_peer.wireguard_peer.download_config` [ANY]
- `press.doctype.wireguard_peer.wireguard_peer.fetch_peer_private_network` [ANY]
- `press.doctype.wireguard_peer.wireguard_peer.generate_config` [ANY]
- `press.doctype.wireguard_peer.wireguard_peer.ping_peer` [ANY]
- `press.doctype.wireguard_peer.wireguard_peer.setup_wireguard` [ANY]

## `press.report.agent_versions.agent_versions`
- `press.report.agent_versions.agent_versions.update_agent` [ANY]

## `press.report.aws_rightsizing_recommendation.aws_rightsizing_recommendation`
- `press.report.aws_rightsizing_recommendation.aws_rightsizing_recommendation.rightsize` [ANY]

## `press.report.mariadb_process_list.mariadb_process_list`
- `press.report.mariadb_process_list.mariadb_process_list.kill` [ANY]

## `press.report.marketplace_app_repository_visibility.marketplace_app_repository_visibility`
- `press.report.marketplace_app_repository_visibility.marketplace_app_repository_visibility.send_emails` [ANY]

## `saas.api.auth`
- `saas.api.auth.is_access_token_valid` [ANY] (guest)

## `saas.doctype.product_trial_request.product_trial_request`
- `saas.doctype.product_trial_request.product_trial_request.get_setup_wizard_payload` [ANY]

## `utils.dns`
- `utils.dns.create_dns_record` [ANY] - Check if site needs dns records and creates one.

## `utils.telemetry`
- `utils.telemetry.capture_read_event` [ANY] (guest)

## `www.dashboard`
- `www.dashboard.get_context_for_dev` [POST] (guest)

## `www.marketplace.index`
- `www.marketplace.index.filter_by_category` [ANY] (guest)
- `www.marketplace.index.search` [ANY] (guest)

