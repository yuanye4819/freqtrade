<script setup lang="ts">
import type { BotDescriptor } from '@/types';
import { useI18n } from 'vue-i18n';
const props = defineProps<{
  bot: BotDescriptor;
}>();
const emit = defineEmits<{ cancelled: []; saved: [] }>();

const botStore = useBotStore();
const { t } = useI18n();
const newName = ref<string>('');

onMounted(() => {
  newName.value = props.bot.botName;
});

const save = () => {
  botStore.updateBot(props.bot.botId, {
    botName: newName.value,
  });

  emit('saved');
};
</script>

<template>
  <form class="flex w-full gap-2" @submit.prevent="save">
    <UInput v-model="newName" class="w-full" :placeholder="$t('nav.botName')" autofocus />

    <div class="flex gap-1">
      <UButton type="submit" color="neutral" :title="$t('common.save')" icon="mdi:check" />

      <UButton color="neutral" :title="$t('common.cancel')" @click="$emit('cancelled')" icon="mdi:close">
      </UButton>
    </div>
  </form>
</template>
