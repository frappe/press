<template>
	<AlertBanner
		title="Votre carte a expiré. Veuillez mettre à jour vos informations de paiement pour éviter la suspension du site."
		type="warning"
	>
		<Button class="ml-auto" route="/billing" variant="outline">
			Mettre à jour la carte
		</Button>
	</AlertBanner>
</template>
<script>
import AlertBanner from './AlertBanner.vue'

export default {
	name: 'AlertCardExpired',
	components: { AlertBanner },
}
</script>
