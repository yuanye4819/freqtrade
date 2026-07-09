import type { AlertSeverity } from '@/types/alertTypes';
import { useI18n } from 'vue-i18n';

export function showAlert(message: string, severity: AlertSeverity = 'warning', bot: string = '') {
  const { t } = useI18n();
  const alertStore = useAlertsStore();

  alertStore.addAlert({
    message,
    title: bot ? t('notifications.botPrefix', { bot }) : t('notifications.notification'),
    severity,
    timeout: 5000,
  });
}

export function useAlertForBot(botName: string) {
  return {
    showAlert: (message: string, severity: AlertSeverity = 'warning') => {
      showAlert(message, severity, botName);
    },
  };
}

export type ShowAlertType = typeof showAlert;
