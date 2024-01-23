<template>
	<Dialog
		:options="{
			title: 'SSH Access',
			size: 'xl'
		}"
		v-model="show"
	>
		<template #body-content>
			<div v-if="certificate" class="space-y-4">
				<div class="space-y-2">
					<h4 class="text-base font-semibold text-gray-700">Step 1</h4>
					<div class="space-y-1">
						<p class="text-base">
							Execute the following shell command to store the SSH certificate
							locally.
						</p>
						<ClickToCopyField :textContent="certificateCommand" />
					</div>
				</div>

				<div class="space-y-2">
					<h4 class="text-base font-semibold text-gray-700">Step 2</h4>
					<div class="space-y-1">
						<p class="text-base">
							Execute the following shell command to SSH into your bench
						</p>
						<ClickToCopyField :textContent="sshCommand" />
					</div>
				</div>
			</div>
			<div v-else>
				<p class="mb-4 text-base">
					You will need an SSH certificate to get SSH access to your bench. This
					certificate will work only with your public-private key pair and will
					be valid for 6 hours.
				</p>
				<p class="text-base">
					Please refer to the
					<a href="/docs/benches/ssh" class="underline"
						>SSH Access documentation</a
					>
					for more details.
				</p>
			</div>
		</template>
		<template #actions v-if="!certificate">
			<Button
				:loading="$releaseGroup.generateCertificate.loading"
				@click="
					async () => {
						await $releaseGroup.generateCertificate.fetch();
						await $releaseGroup.getCertificate.reload();
					}
				"
				variant="solid"
				class="w-full"
				>Generate SSH Certificate</Button
			>
		</template>
		<ErrorMessage
			class="mt-3"
			:message="$releaseGroup.generateCertificate.error"
		/>
	</Dialog>
</template>

<script>
import { getCachedDocumentResource } from 'frappe-ui';

export default {
	props: ['bench', 'releaseGroup'],
	data() {
		return {
			show: true
		};
	},
	mounted() {
		this.$releaseGroup.getCertificate.submit();
	},
	computed: {
		$releaseGroup() {
			return getCachedDocumentResource('Release Group', this.releaseGroup);
		},
		certificate() {
			return this.$releaseGroup.getCertificate.data;
		},
		sshCommand() {
			return `ssh ${this.bench?.name}@${this.bench?.proxyServer} -p 2222`;
		},
		certificateCommand() {
			if (this.certificate) {
				return `echo '${this.certificate.ssh_certificate?.trim()}' > ~/.ssh/id_${
					this.certificate.key_type
				}-cert.pub`;
			}
			return null;
		}
	}
};
</script>
