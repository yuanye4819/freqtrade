<script setup lang="ts">
import type { Trade } from '@/types';
import { useI18n } from 'vue-i18n';

const colorStore = useColorStore();
const { t } = useI18n();

defineProps<{
  trade: Trade;
  stakeCurrency: string;
}>();

const { showTradeCustomData } = useTradeCustomData();
</script>

<template>
  <div class="text-start grid md:grid-cols-[repeat(auto-fit,minmax(500px,1fr))] gap-4 px-2">
    <div class="">
      <div class="flex justify-between items-center border-b">
        <h5 class="text-xl font-semibold w-full block mb-1">{{ $t('trade.general') }}</h5>
        <UButton
          size="sm"
          variant="outline"
          color="neutral"
          @click="showTradeCustomData({ tradeId: trade.trade_id })"
          :label="$t('trade.showCustomData')"
          icon="mdi:database-search"
        />
      </div>
      <ValuePair :description="$t('trade.tradeId')">{{ trade.trade_id }}</ValuePair>
      <ValuePair :description="$t('trade.pair')">{{ trade.pair }}</ValuePair>

      <ValuePair :description="$t('trade.openDate')">{{ timestampms(trade.open_timestamp) }}</ValuePair>
      <ValuePair v-if="trade.enter_tag" :description="$t('trade.entryTag')">{{ trade.enter_tag }}</ValuePair>
      <ValuePair v-if="trade.is_open" :description="$t('trade.stake')">
        {{ formatPriceCurrency(trade.stake_amount, stakeCurrency) }}
        <template v-if="trade.trading_mode !== 'spot'">
          ({{ trade.leverage }}x)
          <span :title="$t('trade.positionValue')" class="italic">{{
            formatPriceCurrency(trade.amount * trade.open_rate, stakeCurrency)
          }}</span>
        </template>
      </ValuePair>
      <ValuePair v-if="!trade.is_open" :description="$t('trade.totalStake')">
        {{ formatPriceCurrency(trade.max_stake_amount ?? trade.stake_amount, stakeCurrency) }}
        {{ trade.trading_mode !== 'spot' ? `(${trade.leverage}x)` : '' }}
      </ValuePair>
      <ValuePair :description="$t('trade.amount')">{{ formatPrice(trade.amount) }}</ValuePair>
      <ValuePair :description="$t('trade.openRate')">{{ formatPrice(trade.open_rate) }}</ValuePair>
      <ValuePair v-if="trade.is_open && trade.current_rate" :description="$t('trade.currentRate')">
        {{ formatPrice(trade.current_rate) }}
        <span :title="$t('trade.currentValueTitle')" class="italic">
          ({{ formatPriceCurrency(trade.stake_amount + (trade.profit_abs ?? 0), stakeCurrency) }})
        </span>
      </ValuePair>
      <ValuePair v-if="!trade.is_open && trade.close_rate" :description="$t('trade.closeRate')">{{
        formatPrice(trade.close_rate)
      }}</ValuePair>

      <ValuePair v-if="trade.close_timestamp" :description="$t('trade.closeDate')">{{
        timestampms(trade.close_timestamp)
      }}</ValuePair>
      <ValuePair
        v-if="trade.is_open && trade.realized_profit && !trade.total_profit_abs"
        :description="$t('trade.realizedProfit')"
      >
        <TradeProfit :trade="trade" mode="realized" />
      </ValuePair>
      <ValuePair v-if="trade.is_open && trade.total_profit_abs" :description="$t('trade.totalProfit')">
        <TradeProfit :trade="trade" mode="total" />
      </ValuePair>
      <ValuePair
        v-if="trade.profit_ratio && trade.profit_abs"
        :description="trade.is_open ? $t('trade.currentProfit') : $t('trade.closeProfit')"
      >
        <TradeProfit :trade="trade" />
      </ValuePair>
      <BaseCollapsible :title="$t('trade.details')" class="px-2 pb-2">
        <ValuePair v-if="trade.min_rate" :description="$t('trade.minRate')">{{
          formatPrice(trade.min_rate)
        }}</ValuePair>
        <ValuePair v-if="trade.max_rate" :description="$t('trade.maxRate')">{{
          formatPrice(trade.max_rate)
        }}</ValuePair>
        <ValuePair :description="$t('trade.openFees')">
          {{ trade.fee_open_cost }} {{ trade.quote_currency }}
          <span v-if="trade.quote_currency !== trade.fee_open_currency">
            {{ $t('trade.inCurrency', { currency: trade.fee_open_currency }) }}
          </span>
          ({{ formatPercent(trade.fee_open) }})
        </ValuePair>
        <ValuePair v-if="trade.fee_close_cost && trade.fee_close" :description="$t('trade.feesClose')">
          {{ trade.fee_close_cost }} {{ trade.fee_close_currency }} ({{
            formatPercent(trade.fee_close)
          }})
        </ValuePair>
      </BaseCollapsible>
    </div>
    <div class="mt-2 lg:mt-0">
      <h5 class="text-xl font-semibold border-b pb-1 w-full block mb-1">{{ $t('trade.stoploss') }}</h5>
      <ValuePair :description="$t('trade.stoploss')">
        {{ formatPercent(trade.stop_loss_ratio) }} |
        {{ formatPrice(trade.stop_loss_abs) }}
      </ValuePair>
      <ValuePair
        :description="$t('trade.atRisk')"
        :help="$t('trade.atRiskHelp')"
      >
        {{
          formatPriceCurrency(trade.stake_amount * Math.abs(trade.stop_loss_ratio), stakeCurrency)
        }}
      </ValuePair>
      <ValuePair
        v-if="trade.is_open && trade.stoploss_current_dist_ratio && trade.stoploss_current_dist"
        :description="$t('trade.currentStoplossDist')"
      >
        {{ formatPercent(trade.stoploss_current_dist_ratio) }} |
        {{ formatPrice(trade.stoploss_current_dist) }}
      </ValuePair>
      <ValuePair
        v-if="trade.initial_stop_loss_pct && trade.initial_stop_loss_abs"
        :description="$t('trade.initialStoploss')"
      >
        {{ formatPercent(trade.initial_stop_loss_pct / 100) }} |
        {{ formatPrice(trade.initial_stop_loss_abs) }}
      </ValuePair>
      <ValuePair v-if="trade.stoploss_last_update_timestamp" :description="$t('trade.stoplossLastUpdated')">
        {{ timestampms(trade.stoploss_last_update_timestamp) }}
      </ValuePair>
      <div v-if="trade.trading_mode !== undefined && trade.trading_mode !== 'spot'">
        <h5 class="text-xl font-semibold border-b pb-1 w-full block mb-1">{{ $t('trade.futuresMargin') }}</h5>
        <ValuePair :description="$t('trade.direction')">
          {{ trade.is_short ? $t('trade.short') : $t('trade.long') }} - {{ trade.leverage }}x
        </ValuePair>
        <ValuePair v-if="trade.funding_fees !== undefined" :description="$t('trade.fundingFees')">
          {{ formatPrice(trade.funding_fees) }}
        </ValuePair>
        <ValuePair v-if="trade.interest_rate !== undefined" :description="$t('trade.interestRate')">
          {{ formatPrice(trade.interest_rate) }}
        </ValuePair>
        <ValuePair v-if="trade.liquidation_price !== undefined" :description="$t('trade.liquidationPrice')">
          {{ formatPrice(trade.liquidation_price) }}
        </ValuePair>
      </div>
      <BaseCollapsible
        v-if="trade.orders"
        :title="$t('trade.orders') + (trade.orders.length > 1 ? ` [${trade.orders.length}]` : '')"
        class="px-2 pb-2"
      >
        <div
          v-for="(order, key) in trade.orders"
          :key="key"
          class="flex items-center gap-1 2"
          :title="`${order.ft_order_side} ${order.order_type} order for ${formatPriceCurrency(
            order.amount,
            trade.base_currency ?? '',
          )} at ${formatPriceCurrency(
            order.safe_price,
            trade.quote_currency ?? '',
          )}, filled ${formatPrice(order.filled)}`"
        >
          (#{{ key + 1 }})
          <i-mdi-triangle
            v-if="order.ft_order_side === 'buy'"
            class="me-1"
            :style="{
              color: colorStore.colorUp,
            }"
            style="font-size: 0.6rem"
          />
          <i-mdi-triangle-down
            v-else
            class="me-1"
            :style="{ color: colorStore.colorDown }"
            style="font-size: 0.6rem"
          />
          <DateTimeTZ v-if="order.order_timestamp" :date="order.order_timestamp" show-timezone />
          <b
            class="ms-1"
            :style="{
              color: order.ft_order_side === 'buy' ? colorStore.colorUp : colorStore.colorDown,
            }"
            >{{ order.ft_order_side }}</b
          >
          for <b>{{ formatPrice(order.safe_price) }}</b> |
          <span v-if="order.remaining && order.remaining !== 0" :title="$t('trade.remaining')"
            >{{ formatPrice(order.remaining, 8) }} /
          </span>
          <span :title="$t('trade.filled')">{{ formatPrice(order.filled ?? 0, 8) }}</span>
          <template v-if="order.ft_order_tag"> | {{ order.ft_order_tag ?? '' }}</template>
        </div>
      </BaseCollapsible>
    </div>
  </div>
</template>
