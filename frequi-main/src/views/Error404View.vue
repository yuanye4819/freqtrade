<template>
  <div>
    <h1 class="mb-5">{{ $t('errors.error404') }}</h1>
    <p class="h4">{{ $t('errors.pageNotFound') }}</p>
    <p>
      {{ $t('errors.dontWorry') }}
      <RouterLink to="/"> <span>{{ $t('errors.mainPage') }}</span> </RouterLink>.
    </p>
  </div>
</template>
