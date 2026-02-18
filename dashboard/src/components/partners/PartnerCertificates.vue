<template>
	<div class="p-5">
		<ObjectList :options="partnerCertificatesList" />
	</div>
</template>

<script>
import { h } from 'vue';
import { FeatherIcon, Tooltip } from 'frappe-ui';
import { icon, renderDialog } from '../../utils/components';
import ObjectList from '../ObjectList.vue';
import PartnerCertificateRequest from './PartnerCertificateRequest.vue';
import LinkCertificate from './LinkCertificate.vue';
import CertificationStatus from './CertificationStatus.vue';
export default {
	name: 'PartnerCertificates',
	components: {
		ObjectList,
		PartnerCertificateRequest,
		LinkCertificate,
		CertificationStatus,
	},
	data() {
		return {
			showApplyForCertificateDialog: false,
		};
	},
	computed: {
		partnerCertificatesList() {
			return {
				doctype: 'Partner Certificate',
				fields: ['free', 'certificate_link'],
				filters: {
					team: this.$team.doc.name,
				},
				columns: [
					{
						label: 'Member Name',
						fieldname: 'partner_member_name',
						width: 0.8,
					},
					{
						label: 'Member Email',
						fieldname: 'partner_member_email',
						width: 0.8,
					},
					{
						label: 'Issued On',
						fieldname: 'issue_date',
						width: 0.5,
						format(value) {
							return Intl.DateTimeFormat('en-US', {
								year: 'numeric',
								month: 'long',
								day: 'numeric',
							}).format(new Date(value));
						},
					},
					{
						label: 'Course',
						fieldname: 'course',
						format(value) {
							return value == 'frappe-developer-certification'
								? 'Framework'
								: 'ERPNext';
						},
						width: 0.6,
					},
					{
						label: 'Version',
						fieldname: 'version',
						width: 0.4,
						align: 'center',
					},
					{
						label: 'Free',
						fieldname: 'free',
						type: 'Component',
						align: 'center',
						width: 0.4,
						component({ row }) {
							if (row.free) {
								return h(
									Tooltip,
									{
										text: 'Free Certification',
									},
									() =>
										h(FeatherIcon, {
											name: 'check-circle',
											class: 'h-4 w-4 text-green-600',
										}),
								);
							}
						},
					},
					{
						label: 'Certificate Link',
						type: 'Button',
						align: 'center',
						Button({ row }) {
							return {
								label: 'View',
								slots: {
									prefix: icon('external-link'),
								},
								onClick: (e) => {
									e.stopPropagation();
									window.open(row.certificate_link);
								},
							};
						},
						width: 0.5,
					},
				],
				documentation: 'https://school.frappe.io',
				actions() {
					return [
						{
							label: 'Apply for Certification',
							slots: {
								prefix: icon('plus'),
							},
							onClick: () => {
								renderDialog(
									h(PartnerCertificateRequest, {
										show: true,
										onSuccess: () => {
											console.log('success');
										},
									}),
								);
							},
						},
						{
							label: 'Link Certificate',
							slots: {
								prefix: icon('link'),
							},
							onClick: () => {
								renderDialog(
									h(LinkCertificate, {
										show: true,
										onSuccess: () => {
											console.log('Certificate linked successfully');
										},
									}),
								);
							},
						},
					];
				},
				moreActions() {
					return [
						{
							label: 'Check Certification Status',
							onClick: () => {
								renderDialog(
									h(CertificationStatus, {
										show: true,
									}),
								);
							},
						},
					];
				},
				filterControls() {
					return [
						{
							type: 'select',
							fieldname: 'course',
							label: 'Course',
							options: [
								{ label: 'Framework', value: 'frappe-developer-certification' },
								{ label: 'ERPNext', value: 'erpnext-distribution' },
							],
						},
					];
				},
				orderBy: 'creation desc',
			};
		},
	},
};
</script>
