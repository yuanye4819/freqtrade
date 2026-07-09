<template>
  <div class="mt-5">
    <div class="flex justify-center">
      <BotList class="max-w-xl" />
    </div>
    <USeparator class="my-5" />
    <AppIcon class="my-5 sm:w-80 sm:h-80 w-64 h-64" />

    <h1 class="font-bold text-2xl sm:text-4xl mb-4 transition-all">
      {{ $t('home.welcomeTo') }} <AppText class="text-2xl! sm:text-4xl!" />
    </h1>
    <div>{{ $t('home.pageDescription') }}</div>
    <USeparator class="my-5" />
    <p class="mb-2">
      {{ $t('home.helpText') }}
      <a
        class="text-primary underline cursor-pointer"
        href="https://www.freqtrade.io/en/latest/"
        target="_blank"
      >
        {{ $t('home.documentation') }}
      </a>
      .
    </p>

    <p class="mb-5">{{ $t('home.haveFun') }}</p>
  </div>
</template>
