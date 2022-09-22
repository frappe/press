<template>
	<CardWithDetails :title="title" :subtitle="subtitle" :showDetails="playName">
		<div>
			<router-link
				v-for="play in $resources.plays.data"
				class="block cursor-pointer rounded-md px-2.5"
				:class="playName === play.name ? 'bg-gray-100' : 'hover:bg-gray-50'"
				:key="play.name"
				:to="playRoute(play)"
			>
				<ListItem :title="play.play" :description="formatDate(play.creation)">
					<template v-slot:actions>
						<Badge
							v-if="
								runningPlay &&
								runningPlay.id == play.name &&
								runningPlay.status !== 'Success'
							"
							:status="runningPlay.status"
							:colorMap="$badgeStatusColorMap"
						>
							{{ runningPlay.status }}
						</Badge>
						<Badge
							v-else-if="play.status != 'Success'"
							:status="play.status"
							:colorMap="$badgeStatusColorMap"
						>
							{{ play.status }}
						</Badge>
					</template>
				</ListItem>
				<div class="border-b"></div>
			</router-link>
			<div class="py-3" v-if="!$resources.plays.lastPageEmpty">
				<Button
					:loading="$resources.plays.loading"
					loadingText="Loading..."
					@click="pageStart += 10"
				>
					Load more
				</Button>
			</div>
		</div>
		<template #details>
			<PlaysDetail :playName="playName" />
		</template>
	</CardWithDetails>
</template>
<script>
import CardWithDetails from '@/components/CardWithDetails.vue';
import PlaysDetail from './PlaysDetail.vue';
export default {
	name: 'AnsiblePlays',
	props: ['title', 'subtitle', 'resource', 'playName', 'playRoute'],
	components: { PlaysDetail, CardWithDetails },
	data() {
		return {
			pageStart: 0,
			runningPlay: null
		};
	},
	resources: {
		plays() {
			return this.resource(this.pageStart);
		}
	},
	mounted() {
		this.$socket.on('ansible_play_update', this.onAnsiblePlayUpdate);
	},
	unmounted() {
		this.$socket.off('ansible_play_update', this.onAnsiblePlayUpdate);
	},
	methods: {
		onAnsiblePlayUpdate(data) {
			if (data.id === this.playName) {
				this.runningPlay = data;
				if (this.runningPlay.status === 'Success') {
					setTimeout(() => {
						// calling reload immediately does not fetch the latest status
						// so adding 1 sec delay
						this.$resources.plays.reset();
						this.$resources.plays.reload();
					}, 1000);
				}
			}
		}
	}
};
</script>
