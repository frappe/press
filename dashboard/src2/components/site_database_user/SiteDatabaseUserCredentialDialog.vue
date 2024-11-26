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
				</div>
				<div class="pb-2 pt-5">
					<p class="mb-2 text-base font-semibold text-gray-700">
						Using MariaDB Client
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
			</div>
		</template>
	</Dialog>
</template>
<script>
import ClickToCopyField from '../ClickToCopyField.vue';

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
						method: 'get_credential'
					};
				},
				initialData: {},
				auto: true
			};
		}
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
			}
		}
	}
};
</script>
