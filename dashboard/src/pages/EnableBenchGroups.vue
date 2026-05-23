<template>
	<div>
		<div
			class="mx-auto max-w-2xl rounded-lg border-0 px-2 py-8 sm:border sm:p-8 space-y-8 mt-10"
		>
			<div class="prose prose-sm max-w-none">
				<h1 class="text-2xl font-semibold">Benches</h1>
				<p class="text-p-base">
					Avec les Benches, vous avez plus de contrôle. Vous pouvez choisir quelles apps
					ajouter, quelles apps mettre à jour, dans quelle région déployer et plus encore.
				</p>
			</div>
			<div class="space-y-3">
				<h2 class="text-sm font-semibold tracking-wide text-ink-gray-7">
					Fonctionnalités
				</h2>
				<ul class="space-y-2">
					<li v-for="f in features" :key="f" class="flex items-center gap-2">
						<GreenCheckIcon class="h-4 w-4 shrink-0" />
						<span class="text-sm text-ink-gray-7">{{ f }}</span>
					</li>
				</ul>
				<div>
					<Link
						href="https://docs.frappe.io/cloud/what-are-benches-and-bench-groups"
						target="_blank"
						class="inline-flex items-center text-sm font-medium text-indigo-600 hover:text-indigo-700"
						>En savoir plus →</Link
					>
				</div>
				<div v-if="!onboardingComplete" class="pt-2">
					<p class="text-sm text-ink-gray-7">
						Terminez l'intégration pour commencer à utiliser les Benches.
					</p>
					<Button
						:route="{ name: 'Welcome' }"
						label="Continuer l'intégration"
						class="mt-3"
					/>
				</div>
			</div>
		</div>
	</div>
</template>
<script>
import Link from '@/components/Link.vue';

export default {
	name: 'EnableBenchGroups',
	components: { Link },
	data() {
		return {
			features: [
				'Déploiements conteneurisés',
				'Déploiement d\'apps personnalisées',
				'Accès à plus de 150 apps marketplace',
				'Multi-environnement (ex. Staging, Production)',
				'Scripts serveur',
				'Accès SSH',
				'Workers dédiés',
			],
		};
	},
	computed: {
		benchesEnabled() {
			return Boolean(this.$team.doc.benches_enabled);
		},
		onboardingComplete() {
			return Boolean(this.$team.doc.onboarding?.complete);
		},
	},
	mounted() {
		if (this.onboardingComplete && this.$team.doc.benches_enabled) {
			this.$router.push({ name: 'Release Group List' });
		}
	},
};
</script>
