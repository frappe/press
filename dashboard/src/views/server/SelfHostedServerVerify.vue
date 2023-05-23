<template>
<div>
		<h2>Add this SSH Key to the Server</h2>
		<ClickToCopyField :textContent="ssh_key"/>

</div>

</template>
<script>
import ClickToCopyField from '@/components/ClickToCopyField.vue';
export default{
	name: 'SelfHostedServerVerify',
	props:["ssh_key"],
	components:{
		ClickToCopyField
	}
}
</script>
