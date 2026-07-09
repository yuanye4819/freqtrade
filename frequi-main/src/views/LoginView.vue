<script setup lang="ts"></script>

<template>
  <div class="max-w-xl mx-auto p-4 my-5">
    <DraggableContainer :header="$t('login.freqtradeBotLogin')" class="px-4 py-2">
      <BotLogin />
    </DraggableContainer>
  </div>
</template>
