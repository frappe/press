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
					},
					{
						label: 'Member Email',
						fieldname: 'partner_member_email',
					},
					{
						label: 'Issued On',
						fieldname: 'issue_date',
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
						width: 0.5,
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
					},
				],
				orderBy: 'creation desc',
			};
		},
	},
};
</script>
