<template>
	<div class="p-5">
		<ObjectList :options="partnerCertificatesList" />
	</div>
</template>

<script>
import { h } from 'vue';
import { FeatherIcon, Tooltip } from 'frappe-ui';
import { icon } from '../utils/components';
import ObjectList from '../components/ObjectList.vue';
export default {
	name: 'PartnerAdminCertificates',
	components: {
		ObjectList,
	},
	computed: {
		partnerCertificatesList() {
			return {
				doctype: 'Partner Certificate',
				fields: ['free', 'certificate_link'],
				columns: [
					{
						label: 'Member Name',
						fieldname: 'partner_member_name',
						width: 0.8,
						class: 'truncate',
						format: (value) => {
							if (!value) return '';
							return value.length > 25 ? `${value.slice(0, 25)}...` : value;
						},
					},
					{
						label: 'Member Email',
						fieldname: 'partner_member_email',
						width: 0.8,
						class: 'truncate',
						format: (value) => {
							if (!value) return '';
							return value.length > 25 ? `${value.slice(0, 25)}...` : value;
						},
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
						width: 0.5,
					},
					{
						label: 'Partner',
						fieldname: 'team',
						width: 0.8,
						class: 'truncate',
						format: (value) => {
							if (!value) return '';
							return value.length > 25 ? `${value.slice(0, 25)}...` : value;
						},
					},
					{
						label: 'Version',
						fieldname: 'version',
						width: 0.3,
						align: 'center',
					},
					{
						label: 'Free',
						fieldname: 'free',
						type: 'Component',
						align: 'center',
						width: 0.3,
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
						width: 0.5,
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
					},
				],
				filterControls() {
					return [
						{
							type: 'data',
							fieldname: 'search-text',
							label: 'Search',
						},
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
