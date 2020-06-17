<template>
	<div>
		<Section
			title="Request Logs"
			description="This is a log of web requests on your site."
		>
			<SectionCard class="md:w-2/3">
				<div
					class="text-base cursor-pointer"
					v-for="log in requestLogs.data"
					:key="log.name"
					@click="showDetailsForLog = showDetailsForLog === log ? null : log"
				>
					<div
						class="flex items-center justify-between px-6 py-3 hover:bg-gray-50"
					>
						<div class="flex">
							<div class="flex-shrink-0 w-16">
								<Badge
									:color="{ GET: 'green', POST: 'orange' }[log.http_method]"
								>
									{{ log.http_method }}
								</Badge>
							</div>

							<div class="inline-block pr-2 font-mono break-all">
								{{ log.url }}
							</div>
						</div>
						<div class="flex flex-shrink-0">
							<FormatDate>{{ log.timestamp }}</FormatDate>
							<FeatherIcon
								:name="
									showDetailsForLog === log ? 'chevron-up' : 'chevron-down'
								"
								class="w-4 h-4 ml-2"
							/>
						</div>
					</div>
					<div class="px-6">
						<DescriptionList
							class="py-4 pl-16"
							v-show="showDetailsForLog === log"
							:items="[
								{
									label: 'Status Code',
									value: log.status_code
								},
								{
									label: 'IP',
									value: log.ip
								},
								{
									label: 'Duration',
									value: `${log.duration / 1000} ms`
								},
								{
									label: 'Length',
									value: formatBytes(log.length)
								}
							]"
						/>
					</div>
				</div>
				<div class="px-6 my-2" v-if="!$resources.requestLogs.lastPageEmpty">
					<Button
						:loading="$resources.requestLogs.loading"
						loadingText="Fetching..."
						@click="pageStart += 20"
					>
						Load more
					</Button>
				</div>
			</SectionCard>
		</Section>
	</div>
</template>

<script>
import DescriptionList from '@/components/DescriptionList';

export default {
	name: 'SiteRequestLogs',
	props: ['site'],
	components: {
		DescriptionList
	},
	data() {
		return {
			showDetailsForLog: null,
			pageStart: 0
		};
	},
	resources: {
		requestLogs() {
			return {
				method: 'press.api.site.request_logs',
				params: {
					name: this.site.name,
					start: this.pageStart
				},
				auto: true,
				paged: true,
				keepData: true
			};
		}
	}
};
</script>
