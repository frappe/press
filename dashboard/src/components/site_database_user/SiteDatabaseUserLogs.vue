<template>
	<Dialog
		:options="{
			title: `Database User (${db_user_name}) Logs`,
			size: '5xl',
		}"
		v-model="showDialog"
	>
		<template #body-content>
			<div>
				<!-- Top Bar -->
				<form
					class="flex w-full flex-row items-center gap-2"
					@submit.prevent="this.$resources.logs.submit()"
				>
					<FormControl
						class="w-full"
						type="text"
						size="sm"
						variant="subtle"
						icon-left="search"
						placeholder="Search Keywords (Optional)"
						v-model="search_string"
					/>
					<FormControl
						class="w-full"
						type="text"
						size="sm"
						variant="subtle"
						placeholder="Client IP (Optional)"
						v-model="client_ip"
					/>
					<div class="min-w-[11rem] max-w-[11rem] text-base">
						<DateTimePicker
							v-model="start_time"
							variant="subtle"
							placeholder="Start Time"
							label="Start Time"
							:disabled="false"
						/>
					</div>
					<div class="min-w-[11rem] max-w-[11rem] text-base">
						<DateTimePicker
							v-model="end_time"
							variant="subtle"
							placeholder="End Time"
							:disabled="false"
						/>
					</div>
					<Button
						variant="solid"
						theme="gray"
						size="sm"
						loadingText="Searching"
						:loading="this.$resources.logs.loading"
						iconLeft="search"
						@click="this.$resources.logs.submit()"
					>
						Search
					</Button>
				</form>

				<!-- Result -->
				<div class="mt-5">
					<div
						v-if="this.$resources.logs.loading"
						class="flex h-[14.5rem] w-full items-center justify-center gap-2 py-20 text-base text-gray-700"
					>
						<Spinner class="w-4" /> Fetching logs...
					</div>
					<div v-else>
						<SQLResultTable
							:columns="['Timestamp', 'Client IP', 'Query', 'Duration (ms)']"
							:data="this.logs"
							:hideIndexColumn="true"
							:isTruncateText="true"
							:truncateLength="70"
						/>
						<p class="mt-2 text-sm text-gray-700">
							<span class="font-semibold">NOTE :</span> Search result will show
							max 500 logs.
						</p>
					</div>
				</div>
			</div>
			<ErrorMessage :message="this.$resources?.logs?.error" class="mt-2" />
		</template>
	</Dialog>
</template>
<script>
import { ErrorMessage, FormControl } from 'frappe-ui';
import { icon } from '../../utils/components';
import { DashboardError } from '../../utils/error';
import { DateTimePicker } from 'frappe-ui';
import SQLResultTable from '../devtools/database/SQLResultTable.vue';

export default {
	name: 'SiteDatabaseUserLogs',
	props: ['name', 'db_user_name'],
	$emit: ['update:modelValue', 'hide'],
	components: {
		FormControl,
		icon,
		DateTimePicker,
		SQLResultTable,
		ErrorMessage,
	},
	data() {
		return {
			start_time: null,
			end_time: null,
			search_string: '',
			client_ip: '',
		};
	},
	mounted() {
		const now = new Date();
		this.end_time = now.toLocaleString();
		const oneHourAgo = new Date(now.getTime() - 60 * 60 * 1000);
		this.start_time = oneHourAgo.toLocaleString();

		this.$resources.logs.submit();
	},
	resources: {
		logs() {
			return {
				url: 'press.api.client.run_doc_method',
				initialData: {},
				auto: false,
				makeParams: () => {
					return {
						dt: 'Site Database User',
						dn: this.name,
						method: 'fetch_logs',
						args: {
							start_timestamp: parseInt(
								new Date(this.start_time).getTime() / 1000,
							),
							end_timestamp: parseInt(new Date(this.end_time).getTime() / 1000),
							search_string: this.search_string,
							client_ip: this.client_ip,
						},
					};
				},
				validate() {
					let start_time_date = new Date(this.start_time);
					let end_time_date = new Date(this.end_time);
					if (!(start_time_date || start_time_date == 'Invalid Date')) {
						throw new DashboardError('Please choose a valid start time');
					}

					if (!(end_time_date || end_time_date == 'Invalid Date')) {
						throw new DashboardError('Please choose a valid end time');
					}

					if (start_time_date >= end_time_date) {
						throw new DashboardError('Start time must be before end time');
					}
				},
				onSuccess: (data) => {
					if (data?.message?.loading) {
						setTimeout(this.fetchTableSchemas, 5000);
					}
				},
			};
		},
	},
	computed: {
		showDialog: {
			get() {
				return this.modelValue;
			},
			set(value) {
				this.$emit('update:modelValue', value);
				if (!value) {
					this.$emit('hide');
				}
			},
		},
		logs() {
			if (!this.$resources?.logs?.data?.message) return [];
			let data = this.$resources?.logs?.data?.message ?? [];
			let result = [];
			for (let log of data) {
				result.push([
					new Date((log.start_timestamp || 0) * 1000).toLocaleString(),
					log.client_ip,
					log.query,
					log.duration_ms,
				]);
			}
			return result;
		},
	},
	methods: {},
};
</script>
