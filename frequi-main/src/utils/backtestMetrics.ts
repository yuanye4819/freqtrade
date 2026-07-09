import type { StrategyBacktestResult, Trade } from '@/types';
import { useI18n } from 'vue-i18n';

function getSortedTrades(trades: Trade[]): Trade[] {
  const sortedTrades = trades.slice().sort((a, b) => (a.profit_ratio ?? 0) - (b.profit_ratio ?? 0));
  return sortedTrades;
}

function getBestPair(trades: Trade[]) {
  const value = trades[trades.length - 1];
  if (!value) {
    return 'N/A';
  }
  return `${value.pair} ${formatPercent(value.profit_ratio, 2)}`;
}

function getWorstPair(trades: Trade[]) {
  const value = trades[0];
  if (!value) {
    return 'N/A';
  }
  return `${value.pair} ${formatPercent(value.profit_ratio, 2)}`;
}

function useFormatPriceStake(stake_currency_decimals: number, stake_currency: string) {
  const formatPriceStake = (price) => {
    return `${formatPrice(price, stake_currency_decimals)} ${stake_currency}`;
  };
  return formatPriceStake;
}

export function generateBacktestMetricRows(result: StrategyBacktestResult) {
  const sortedTrades = getSortedTrades(result.trades);
  const bestPair = getBestPair(sortedTrades);
  const worstPair = getWorstPair(sortedTrades);
  const pairSummary = result.results_per_pair[result.results_per_pair.length - 1];

  const formatPriceStake = useFormatPriceStake(
    result.stake_currency_decimals,
    result.stake_currency,
  );
  const { t } = useI18n();

  // Transpose Result into readable format
  const shortMetrics =
    result.trade_count_short && result.trade_count_short > 0
      ? [
          { '___ ': '___' },
          {
            [t('backtest.longShort')]: `${result.trade_count_long} / ${result.trade_count_short}`,
          },
          {
            [t('backtest.totalProfitLong')]: `${formatPercent(
              result.profit_total_long || 0,
            )} | ${formatPriceStake(result.profit_total_long_abs)}`,
          },
          {
            [t('backtest.totalProfitShort')]: `${formatPercent(
              result.profit_total_short || 0,
            )} | ${formatPriceStake(result.profit_total_short_abs)}`,
          },
        ]
      : [];

  const walletBalanceMetrics = result.wallet_stats
    ? [
        { '--- Wallet Balance metrics ---': '' },
        {
          [t('backtest.maxDrawdown') + t('backtest.walletBalance')]: formatPercent(result.wallet_stats.max_drawdown_account),
        },
        {
          [t('backtest.maxDrawdownAbs') + t('backtest.walletBalance')]: formatPriceStake(result.wallet_stats.max_drawdown_abs),
        },
        {
          [t('backtest.drawdownDuration') + t('backtest.walletBalance')]: result.wallet_stats.drawdown_duration ?? 'N/A',
        },
        {
          [t('backtest.profitAtDrawdown') + t('backtest.walletBalance')]: `${formatPriceStake(result.wallet_stats.max_drawdown_high)} | ${formatPriceStake(
            result.wallet_stats.max_drawdown_low,
          )}`,
        },
        {
          [t('backtest.drawdownStart') + t('backtest.walletBalance')]: timestampms(result.wallet_stats?.drawdown_start_ts ?? 0),
        },
        { [t('backtest.drawdownEnd') + t('backtest.walletBalance')]: timestampms(result.wallet_stats?.drawdown_end_ts ?? 0) },
        {
          [t('backtest.sortino') + t('backtest.walletBalance')]: formatNumber(result.wallet_stats.sortino, 2),
        },
        {
          [t('backtest.sharpe') + t('backtest.walletBalance')]: formatNumber(result.wallet_stats.sharpe, 2),
        },
        {
          [t('backtest.calmar') + t('backtest.walletBalance')]: formatNumber(result.wallet_stats.calmar, 2),
        },
      ]
    : [];

  const tmp = [
    {
      [t('backtest.totalProfit')]: `${formatPercent(result.profit_total)} | ${formatPriceStake(
        result.profit_total_abs,
      )}`,
    },
    {
      [t('backtest.cagr')]: `${result.cagr ? formatPercent(result.cagr) : 'N/A'}`,
    },
    {
      [t('backtest.sortino')]: formatNumber(result.sortino, 2),
    },
    {
      [t('backtest.sharpe')]: formatNumber(result.sharpe, 2),
    },
    {
      [t('backtest.calmar')]: formatNumber(result.calmar, 2),
    },
    {
      [t('backtest.sqn')]: formatNumber(result.sqn, 2),
    },
    {
      [t('backtest.meanProfitPValue')]: formatNumber(result.p_value, 3),
    },
    {
      [t('backtest.expectancy')]: `${
        result.expectancy
          ? result.expectancy_ratio
            ? `${formatNumber(result.expectancy, 2)} (${formatNumber(result.expectancy_ratio, 2)})`
            : formatNumber(result.expectancy, 2)
          : 'N/A'
      }`,
    },
    {
      [t('backtest.profitFactor')]: formatNumber(result.profit_factor, 3),
    },
    {
      [t('backtest.totalTradesDailyAvg')]: `${result.total_trades} / ${formatNumber(result.trades_per_day, 2)}`,
    },
    // { 'First trade': result.backtest_fi },
    // { 'First trade Pair': result.backtest_best_day },
    {
      [t('backtest.bestDay')]: `${formatPercent(result.backtest_best_day, 2)} | ${formatPriceStake(
        result.backtest_best_day_abs,
      )}`,
    },
    {
      [t('backtest.worstDay')]: `${formatPercent(result.backtest_worst_day, 2)} | ${formatPriceStake(
        result.backtest_worst_day_abs,
      )}`,
    },

    {
      [t('backtest.winDrawLoss')]: `${pairSummary?.wins} / ${pairSummary?.draws} / ${pairSummary?.losses} ${
        isNotUndefined(pairSummary?.winrate)
          ? '(WR: ' +
            formatPercent(
              result.results_per_pair[result.results_per_pair.length - 1]?.winrate ?? 0,
              2,
            ) +
            ')'
          : ''
      }`,
    },
    {
      [t('backtest.daysWinDrawLoss')]: `${result.winning_days} / ${result.draw_days} / ${result.losing_days}`,
    },
    {
      // TODO: min/max/avg trade duration should be aligned with the terminal output
      [t('backtest.minDurationWinners')]: humanizeDurationFromSeconds(result.winner_holding_min_s),
    },
    {
      [t('backtest.avgDurationWinners')]: humanizeDurationFromSeconds(result.winner_holding_avg_s),
    },
    {
      [t('backtest.maxDurationWinners')]: humanizeDurationFromSeconds(result.winner_holding_max_s),
    },
    {
      [t('backtest.minDurationLosers')]: humanizeDurationFromSeconds(result.loser_holding_min_s),
    },
    {
      [t('backtest.avgDurationLosers')]: humanizeDurationFromSeconds(result.loser_holding_avg_s),
    },
    {
      [t('backtest.maxDurationLosers')]: humanizeDurationFromSeconds(result.loser_holding_max_s),
    },
    {
      [t('backtest.maxConsecutiveWinsLoss')]:
        result.max_consecutive_wins === undefined
          ? 'N/A'
          : `${result.max_consecutive_wins} / ${result.max_consecutive_losses}`,
    },
    { [t('backtest.rejectedSignals')]: result.rejected_signals },
    {
      [t('backtest.entryExitTimeouts')]: `${result.timedout_entry_orders} / ${result.timedout_exit_orders}`,
    },
    {
      [t('backtest.canceledTradeEntries')]: result.canceled_trade_entries ?? 'N/A',
    },
    {
      [t('backtest.canceledEntryOrders')]: result.canceled_entry_orders ?? 'N/A',
    },
    {
      [t('backtest.replacedEntryOrders')]: result.replaced_entry_orders ?? 'N/A',
    },

    ...shortMetrics,

    { ___: '___' },
    {
      [t('backtest.minMaxBalanceClosed')]: `${formatPriceStake(result.csum_min)} / ${formatPriceStake(result.csum_max)}`,
    },
    {
      [t('backtest.minMaxBalanceWallet')]: `${formatPriceStake(result.wallet_stats?.low_balance)} / ${formatPriceStake(result.wallet_stats?.high_balance)}`,
    },
    { [t('backtest.marketChange')]: formatPercent(result.market_change) },
    { '___  ': '___' },
    {
      [t('backtest.maxDrawdown')]: formatPercent(result.max_drawdown_account),
    },
    {
      [t('backtest.maxDrawdownAbs')]: formatPriceStake(result.max_drawdown_abs),
    },
    {
      [t('backtest.drawdownDuration')]: result.drawdown_duration ?? 'N/A',
    },
    {
      [t('backtest.profitAtDrawdown')]: `${formatPriceStake(result.max_drawdown_high)} | ${formatPriceStake(
        result.max_drawdown_low,
      )}`,
    },
    { [t('backtest.drawdownStart')]: timestampms(result.drawdown_start_ts) },
    { [t('backtest.drawdownEnd')]: timestampms(result.drawdown_end_ts) },
    ...walletBalanceMetrics,
    { '___    ': '___' },
    {
      [t('backtest.bestPair')]: `${result.best_pair.key} ${formatPercent(result.best_pair.profit_total)}`,
    },
    {
      [t('backtest.worstPair')]: `${result.worst_pair.key} ${formatPercent(result.worst_pair.profit_total)}`,
    },
    { [t('backtest.bestSingleTrade')]: bestPair },
    { [t('backtest.worstSingleTrade')]: worstPair },
  ];
  return tmp;
}

function capitalizeFirstLetter(str: string): string {
  return str.charAt(0).toUpperCase() + str.slice(1);
}

function formatTradingMode(result: StrategyBacktestResult) {
  if (!result.trading_mode || !result.margin_mode) {
    return {};
  }
  const { t } = useI18n();
  const value =
    result.trading_mode === 'spot'
      ? capitalizeFirstLetter(result.trading_mode)
      : `${capitalizeFirstLetter(result.margin_mode)} ${capitalizeFirstLetter(result.trading_mode)}`;
  return { [t('backtest.tradingMode')]: value };
}

export function generateBacktestSettingRows(result: StrategyBacktestResult) {
  const formatPriceStake = useFormatPriceStake(
    result.stake_currency_decimals,
    result.stake_currency,
  );
  const { t } = useI18n();
  const tradingMode = formatTradingMode(result);

  return [
    { [t('backtest.backtestingFrom')]: timestampms(result.backtest_start_ts) },
    { [t('backtest.backtestingTo')]: timestampms(result.backtest_end_ts) },
    ...(Object.keys(tradingMode).length !== 0 ? [tradingMode] : []),
    {
      [t('backtest.btExecutionTime')]: humanizeDurationFromSeconds(
        result.backtest_run_end_ts - result.backtest_run_start_ts,
      ),
    },
    { [t('backtest.maxOpenTrades')]: result.max_open_trades },
    { [t('backtest.timeframe')]: result.timeframe },
    { [t('backtest.timeframeDetail')]: result.timeframe_detail || 'N/A' },
    { [t('backtest.timerange')]: result.timerange },
    { [t('trade.stoploss')]: formatPercent(result.stoploss, 2) },
    { [t('backtest.trailingStoploss')]: result.trailing_stop },
    {
      [t('backtest.trailOnlyOffset')]: result.trailing_only_offset_is_reached,
    },
    { [t('backtest.trailingStopPositive')]: formatNumber(result.trailing_stop_positive) },
    {
      [t('backtest.trailingStopPositiveOffset')]: formatNumber(result.trailing_stop_positive_offset),
    },
    { [t('backtest.customStoploss')]: result.use_custom_stoploss },
    { [t('backtest.roi')]: JSON.stringify(result.minimal_roi) },
    {
      [t('backtest.useExitSignal')]: result.use_exit_signal ?? result.use_sell_signal,
    },
    {
      [t('backtest.exitProfitOnly')]: result.exit_profit_only ?? result.sell_profit_only,
    },
    {
      [t('backtest.exitProfitOffset')]: formatNumber(result.exit_profit_offset ?? result.sell_profit_offset),
    },
    { [t('backtest.enableProtections')]: result.enable_protections },
    {
      [t('backtest.startingBalance')]: formatPriceStake(result.starting_balance),
    },
    {
      [t('backtest.finalBalance')]: formatPriceStake(result.final_balance),
    },
    {
      [t('backtest.avgStakeAmount')]: formatPriceStake(result.avg_stake_amount),
    },
    {
      [t('backtest.totalTradeVolume')]: formatPriceStake(result.total_volume),
    },
  ];
}

/** Selectable options for backtest charts.
 * selection happens through the settings page
 */
export const availableBacktestMetrics = ref([
  { field: 'sqn', header: 'SQN' },
  { field: 'cagr', header: 'Cagr' },
  { field: 'calmar', header: 'Calmar' },
  { field: 'p_value', header: 'Mean profit p-value' },
  { field: 'expectancy', header: 'Expectancy' },
  { field: 'profit_factor', header: 'Profit Factor' },
  { field: 'sharpe', header: 'Sharpe' },
  { field: 'sortino', header: 'Sortino' },
  { field: 'max_drawdown_account', header: 'Max Drawdown', is_ratio: true },
]);
