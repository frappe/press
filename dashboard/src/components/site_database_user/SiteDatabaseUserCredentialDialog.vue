<template>
	<Dialog
		:options="{ title: 'Database Credential', size: '2xl' }"
		v-model="showDialog"
	>
		<template #body-content>
			<div
				v-if="$resources.databaseCredential.loading"
				class="flex w-full items-center justify-center gap-2 py-20 text-gray-700"
			>
				<Spinner class="w-4" /> Loading
			</div>
			<div v-else>
				<div v-if="databaseCredential">
					<p class="mb-2 text-base font-semibold text-gray-700">
						Using an Analytics or Business Intelligence Tool
					</p>
					<p class="mb-2 text-base">
						Use following credentials with your analytics or business
						intelligence tool
					</p>
					<p class="ml-1 font-mono text-sm">
						Host: {{ databaseCredential?.host }}
					</p>
					<p class="ml-1 font-mono text-sm">
						Port: {{ databaseCredential?.port }}
					</p>
					<p class="ml-1 font-mono text-sm">
						Database Name: {{ databaseCredential?.database }}
					</p>
					<p class="ml-1 font-mono text-sm">
						Username: {{ databaseCredential?.username }}
					</p>
					<p class="ml-1 font-mono text-sm">
						Password: {{ databaseCredential?.password }}
					</p>
					<p class="ml-1 font-mono text-sm">Use SSL: Yes</p>
					<p class="ml-1 font-mono text-sm">
						Max Database Connection{{
							databaseCredential?.max_connections > 1 ? 's' : ''
						}}: {{ databaseCredential?.max_connections }}
					</p>
				</div>
				<div class="pb-2 pt-5">
					<p class="mb-2 text-base font-semibold text-gray-700">
						Using MariaDB CLI
					</p>
					<p class="mb-2 text-base">
						Run this command in your terminal to access MariaDB console
					</p>
					<ClickToCopyField class="ml-1" :textContent="dbAccessCommand" />
					<p class="mt-3 text-sm">
						Note: You should have a
						<span class="font-mono">mariadb</span> client installed on your
						computer.
					</p>
				</div>
				<div class="pb-2 pt-5">
					<p class="mb-2 text-base font-semibold text-gray-700">SSL Info</p>
					<p class="text-sm">
						You need to <b>use SSL</b> to connect to the database.
					</p>
					<Button
						class="mt-3"
						:loading="this.$resources.downloadSSLCert.loading"
						loading-text="Downloading Full Chain SSL Certificate (.pem)"
						@click="this.$resources.downloadSSLCert.submit()"
						>Download Full Chain SSL Certificate (.pem)</Button
					>
					<ErrorMessage
						class="mt-2"
						:message="this.$resources.downloadSSLCert.error"
					/>
				</div>
				<div class="pb-2 pt-5">
					<p class="mb-2 text-base font-semibold text-gray-700">Need Help?</p>
					<p class="text-sm">
						Please check out the
						<a
							href="https://docs.frappe.io/cloud/database-users-and-permission-manager#faq"
							target="_blank"
							class="underline"
							>documentation</a
						>
						to get guides on troubleshooting.
					</p>
				</div>
			</div>
		</template>
	</Dialog>
</template>
<script>
import ClickToCopyField from '../ClickToCopyField.vue';
import { toast } from 'vue-sonner';

export default {
	name: 'SiteDatabaseUserCredentialDialog',
	props: ['name', 'modelValue'],
	emits: ['update:modelValue'],
	components: { ClickToCopyField },
	data() {
		return {};
	},
	resources: {
		databaseCredential() {
			return {
				url: 'press.api.client.run_doc_method',
				makeParams: () => {
					return {
						dt: 'Site Database User',
						dn: this.name,
						method: 'get_credential',
					};
				},
				initialData: {},
				auto: true,
			};
		},
		downloadSSLCert() {
			return {
				url: 'press.api.download_ssl_cert',
				makeParams: () => {
					return {
						domain: this.databaseCredential?.host ?? '',
					};
				},
				auto: false,
				onSuccess: (data) => {
					// create a blob and trigger a download
					const blob = new Blob([data], { type: 'text/plain' });
					const filename = `${this.databaseCredential?.host ?? ''}.pem`;
					const link = document.createElement('a');
					link.href = URL.createObjectURL(blob);
					link.download = filename;
					link.click();
					URL.revokeObjectURL(link.href);
					toast.success('SSL Certificate downloaded successfully');
				},
			};
		},
	},
	computed: {
		databaseCredential() {
			return this.$resources?.databaseCredential?.data?.message ?? {};
		},
		dbAccessCommand() {
			if (!this.databaseCredential) return '';
			return `mysql -u ${this.databaseCredential.username} -p -h ${this.databaseCredential.host} -P ${this.databaseCredential.port} --ssl --ssl-verify-server-cert`;
		},
		showDialog: {
			get() {
				return this.modelValue;
			},
			set(value) {
				this.$emit('update:modelValue', value);
			},
		},
	},
};
</script>
