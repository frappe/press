<template>
	<div>
		<Navbar />
		<div class="container mx-auto">
			<slot />
		</div>
	</div>
</template>

<script>
import Navbar from '@/components/Navbar';
export default {
	components: {
		Navbar
	}
};
</script>

<static-query>
query {
  metadata {
    siteName
  }
}
</static-query>
