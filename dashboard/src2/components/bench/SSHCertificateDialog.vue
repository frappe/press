<template>
	<Dialog
		:options="{
			title: 'SSH Access',
			size: 'xl'
		}"
		v-model="show"
	>
		<template #body-content v-if="$bench.doc">
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
			<div class="space-y-2 text-p-base text-gray-700" v-else>
				<p v-if="!$bench.doc.user_ssh_key">
					It looks like you haven't added your SSH public key. Go to
					<router-link
						:to="{ name: 'SettingsDeveloper' }"
						class="underline"
						@click="show = false"
					>
						Developer Settings</router-link
					>
					to add your SSH public key.
				</p>
				<p v-else-if="!$bench.doc.is_ssh_proxy_setup">
					SSH access is not enabled for this bench. Please contact support to
					enable access.
				</p>
				<p v-else>
					You will need an SSH certificate to get SSH access to your bench. This
					certificate will work only with your public-private key pair and will
					be valid for 6 hours.
				</p>
				<p>
					Please refer to the
					<a href="/docs/benches/ssh" class="underline" target="_blank"
						>SSH Access documentation</a
					>
					for more details.
				</p>
			</div>
		</template>
		<template
			#actions
			v-if="
				!certificate &&
				$bench.doc?.is_ssh_proxy_setup &&
				$bench.doc?.user_ssh_key
			"
		>
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
	resources: {
		bench() {
			return {
				type: 'document',
				doctype: 'Bench',
				name: this.bench,
				onSuccess(doc) {
					if (doc.is_ssh_proxy_setup && doc.user_ssh_key) {
						this.$releaseGroup.getCertificate.reload();
					}
				}
			};
		}
	},
	computed: {
		$bench() {
			return this.$resources.bench;
		},
		$releaseGroup() {
			return getCachedDocumentResource('Release Group', this.releaseGroup);
		},
		certificate() {
			return this.$releaseGroup.getCertificate.data;
		},
		sshCommand() {
			if (!this.$bench.doc) return;
			return `ssh ${this.$bench.doc.name}@${this.$bench.doc.proxy_server} -p 2222`;
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
