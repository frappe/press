<template>
	<Card
		title="SSH Key"
		subtitle="SSH public key associated with your account"
		v-if="$account.team.ssh_access_enabled"
	>
		<div v-if="$account.ssh_key">
			<p class="text-sm text-gray-800 font-mono">
				SHA256:{{ $account.ssh_key.ssh_fingerprint }}
			</p>
			<div class="text-base text-gray-700 mt-2">
				Added on
				{{
					$date($account.ssh_key.creation).toLocaleString({
						month: 'short',
						day: 'numeric',
						year: 'numeric'
					})
				}}
			</div>
		</div>
	</Card>
</template>
<script>
export default {
	name: 'AccountSSHKey',
};
</script>
