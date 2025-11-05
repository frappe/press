<template>
	<Dialog v-model="show" :options="{ title: 'Create Snapshot', size: 'xl' }">
		<template #body-content>
			<div
				class="prose prose-sm rounded mt-4 p-2 text-sm text-gray-700 bg-gray-100 border"
			>
				This feature creates a snapshot of both the <b>App Server</b> and
				<b>Database Server</b>.<br /><br />

				<b>Snapshot Modes:</b>
				<ul>
					<li>
						<b>Consistent:</b> Stops services (like the database and containers)
						while taking the snapshot. Your websites will be temporarily down,
						but this ensures a reliable backup that can be restored safely.
					</li>
					<li>
						<b>Non-Consistent:</b> Takes the snapshot without stopping services.
						It's faster and your sites stay online, but the backup might not
						restore perfectly.
					</li>
				</ul>
				<br />
				The snapshot will cost <b>{{ snapshotPlanRate }}</b
				>.
			</div>
			<div class="mt-4 text-sm text-gray-700" label="Consistent Snapshot">
				<Checkbox
					size="sm"
					v-model="consistent_snapshot"
					label="Consistent Snapshot"
				/>
			</div>
			<ErrorMessage
				:message="this.$resources?.create_snapshot?.error"
				class="mt-2"
			/>
			<Button
				class="mt-4 w-full"
				variant="solid"
				theme="gray"
				size="sm"
				:loading="$resources.create_snapshot.loading"
				@click="$resources.create_snapshot.submit()"
			>
				Create Snapshot
			</Button>
		</template>
	</Dialog>
</template>

<script>
import { Checkbox } from 'frappe-ui';
export default {
	name: 'ServerNewSnapshotDialog',
	components: {
		Checkbox,
	},
	props: {
		server: {
			type: String,
			required: true,
		},
		onSnapshotCreated: {
			type: Function,
			default: () => {},
		},
	},
	data() {
		return {
			show: true,
			consistent_snapshot: true,
		};
	},
	resources: {
		options() {
			return {
				url: 'press.api.server.options',
				auto: true,
			};
		},
		create_snapshot() {
			return {
				url: 'press.api.client.run_doc_method',
				makeParams() {
					return {
						dt: 'Server',
						dn: this.server,
						method: 'create_snapshot',
						args: {
							consistent: this.consistent_snapshot,
						},
					};
				},
				onSuccess: () => {
					this.show = false;
					this.onSnapshotCreated();
				},
			};
		},
	},
	computed: {
		options() {
			return this.$resources?.options?.data ?? {};
		},
		snapshotPlanRate() {
			if (!this.$team?.doc?.currency) return -1;
			try {
				let priceField =
					this.$team.doc.currency === 'INR' ? 'price_inr' : 'price_usd';
				return (
					(this.options?.snapshot_plan?.[priceField] || 0) +
					' ' +
					this.$team.doc.currency +
					' / GB / month'
				);
			} catch (error) {
				console.error('Error fetching snapshot plan rate:', error);
				return -1;
			}
		},
	},
};
</script>
