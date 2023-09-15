<template>
	<div class="mx-5 mt-2">
		<div class="pb-20">
			<div class="flex">
				<div class="flex w-full space-x-2 pb-4">
					<FormControl v-model="searchTerm">
						<template #prefix>
							<FeatherIcon name="search" class="w-4 text-gray-600" />
						</template>
					</FormControl>
				</div>
			</div>
			<Table
				:columns="[
					{ label: 'Subject', name: 'id', width: 2 },
					{ label: 'Severity', name: 'severity', width: 1 },
					{ label: 'Affected Versions', name: 'vulnerable_version' },
					{ label: 'Patched Version', name: 'patched_version' }
				]"
				:rows="advisories"
				v-slot="{ rows, columns }"
			>
				<TableHeader />
				<div class="flex items-center justify-center">
					<LoadingText
						class="mt-8"
						v-if="$resources.securityAdvisories.loading"
					/>
					<div v-else-if="rows.length === 0" class="mt-8">
						<div class="text-base text-gray-700">No Data</div>
					</div>
				</div>

				<TableRow v-for="row in rows" :key="row.name" :row="row">
					<TableCell v-for="column in columns">
						<span class="message" v-if="column.name == 'id'">
							<a :href="`${row.html_url}`"> {{ row['summary'] || '' }} </a>
							<p class="mt-1 text-sm text-gray-600">
								{{ row[column.name] }}
							</p>
							<p class="mt-1 text-sm text-gray-600">
								{{ row['published_at'] }}
							</p>
						</span>
						<span class="message" v-else-if="column.name == 'severity'">
							<Badge
								:theme="getTheme(row['severity'])"
								:label="row[column.name]"
							/>
						</span>
						<span
							class="message"
							v-else-if="column.name == 'vulnerable_version'"
						>
							<span v-for="version in row[column.name]">
								<h6 class="text-gray-600">
									{{ version.vulnerable_version_range }}
								</h6>
							</span>
						</span>
						<span class="message" v-else-if="column.name == 'patched_version'">
							<span v-for="version in row[column.name]">
								<h6 class="text-gray-600">
									{{ version.patched_version }}
								</h6>
							</span>
						</span>
						<span v-else class="message">{{ row[column.name] || '' }}</span>
					</TableCell>
				</TableRow>
			</Table>
		</div>
	</div>
</template>

<script>
import Table from '@/components/Table/Table.vue';
import TableHeader from '@/components/Table/TableHeader.vue';
import TableRow from '@/components/Table/TableRow.vue';
import TableCell from '@/components/Table/TableCell.vue';

export default {
	name: 'AppSecurityAdvisories',
	props: ['server'],
	components: {
		Table,
		TableHeader,
		TableRow,
		TableCell
	},
	resources: {
		securityAdvisories() {
			return {
				url: 'press.api.security.fetch_security_advisories',
				params: {
					server: this.server?.name,
					server_type: this.server?.server_type
				},
				auto: true
			};
		}
	},
	computed: {
		advisories() {
			let advisories = [];

			advisories = this.$resources.securityAdvisories.data || [];

			if (this.searchTerm) {
				return advisories.filter(
					advisory =>
						advisory.summary
							.toLowerCase()
							.includes(this.searchTerm.toLowerCase()) ||
						advisory.severity
							.toLowerCase()
							.includes(this.searchTerm.toLowerCase()) ||
						advisory.id.toLowerCase().includes(this.searchTerm.toLowerCase())
				);
			}

			return advisories;
		}
	},
	methods: {
		getTheme(severity) {
			if (severity == 'High') {
				return 'red';
			} else if (severity == 'Medium') {
				return 'orange';
			} else if (severity == 'Low') {
				return 'green';
			} else {
				return 'gray';
			}
		}
	},
	data() {
		return {
			searchTerm: ''
		};
	}
};
</script>

<style scoped>
.message {
	white-space: pre-wrap;
	line-height: 1.5;
}
</style>
