<script setup lang="ts">
import { useI18n } from 'vue-i18n';
import type { StrategyBacktestResult } from '@/types';

const { t } = useI18n();

const props = defineProps<{
  backtestResult: StrategyBacktestResult;
}>();

const backtestResultStats = computed(() => {
  const tmp = generateBacktestMetricRows(props.backtestResult);
  return formatObjectForTable({ value: tmp }, 'metric');
});

const backtestResultSettings = computed(() => {
  // Transpose Result into readable format
  const tmp = generateBacktestSettingRows(props.backtestResult);

  return formatObjectForTable({ value: tmp }, 'setting');
});
</script>

<template>
  <div class="px-0 w-full">
    <div class="flex justify-center">
      <h3 class="font-bold text-2xl mb-2">
        {{ $t('backtest.resultFor', { strategy: backtestResult.strategy_name }) }}
      </h3>
    </div>

    <div class="flex flex-col text-start ms-0 me-2 gap-2">
      <div class="flex flex-col xl:flex-row">
        <div class="px-0 px-xl-0 pe-xl-1 grow">
          <DraggableContainer :header="$t('backtest.strategySettings')">
            <UTable
              :data="backtestResultSettings"
              :columns="[
                { accessorKey: 'setting', header: t('backtest.setting') },
                { accessorKey: 'value', header: t('backtest.value') },
              ]"
            />
          </DraggableContainer>
        </div>
        <div class="px-0 xl:px-0 pt-2 xl:pt-0 xl:ps-1 grow">
          <DraggableContainer :header="$t('backtest.metrics')">
            <UTable
              :data="backtestResultStats"
              :columns="[
                { accessorKey: 'metric', header: t('backtest.metric') },
                { accessorKey: 'value', header: t('backtest.value') },
              ]"
            />
          </DraggableContainer>
        </div>
      </div>
      <BacktestResultTablePer
        :title="$t('backtest.resultsPerEnterTag')"
        :results="backtestResult.results_per_enter_tag"
        :stake-currency="backtestResult.stake_currency"
        :key-header="$t('backtest.enterTag')"
        :stake-currency-decimals="backtestResult.stake_currency_decimals"
      />

      <BacktestResultTablePer
        :title="$t('backtest.resultsPerExitReason')"
        :results="backtestResult.exit_reason_summary ?? []"
        :stake-currency="backtestResult.stake_currency"
        :key-header="$t('backtest.exitReason')"
        :stake-currency-decimals="backtestResult.stake_currency_decimals"
      />

      <BacktestResultTablePer
        v-if="backtestResult.mix_tag_stats"
        :title="$t('backtest.resultsMixedTag')"
        :results="backtestResult.mix_tag_stats ?? []"
        :stake-currency="backtestResult.stake_currency"
        :key-headers="[t('backtest.enterTag'), t('backtest.exitTag')]"
        :stake-currency-decimals="backtestResult.stake_currency_decimals"
      />

      <BacktestResultTablePer
        :title="$t('backtest.resultsPerPair')"
        :results="backtestResult.results_per_pair"
        :stake-currency="backtestResult.stake_currency"
        :key-header="$t('trade.pair')"
        :stake-currency-decimals="backtestResult.stake_currency_decimals"
      />
      <DraggableContainer v-if="backtestResult.periodic_breakdown" :header="$t('backtest.periodicBreakdown')">
        <BacktestResultPeriodBreakdown :periodic-breakdown="backtestResult.periodic_breakdown">
        </BacktestResultPeriodBreakdown>
      </DraggableContainer>

      <DraggableContainer :header="$t('backtest.singleTrades')">
        <TradeList
          :trades="backtestResult.trades"
          :show-filter="true"
          :stake-currency="backtestResult.stake_currency"
        />
      </DraggableContainer>
    </div>
  </div>
</template>
