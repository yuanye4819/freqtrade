import type { FTWsMessage } from '@/types/wsMessageTypes';
import { FtWsMessageTypes } from '@/types/wsMessageTypes';
import { useI18n } from 'vue-i18n';

export function showNotification(msg: FTWsMessage, botname: string) {
  const { t } = useI18n();
  const settingsStore = useSettingsStore();
  if (settingsStore.notifications && settingsStore.notifications[msg.type]) {
    switch (msg.type) {
      case FtWsMessageTypes.entryFill:
        console.log('entryFill', msg);
        showAlert(
          t('notifications.entryFill', { pair: msg.pair, direction: msg.direction, rate: msg.open_rate }),
          'success',
          botname,
        );
        break;
      case FtWsMessageTypes.exitFill:
        console.log('exitFill', msg);
        showAlert(t('notifications.exitFill', { pair: msg.pair, direction: msg.direction, rate: msg.open_rate }), 'success', botname);
        break;
      case FtWsMessageTypes.exitCancel:
        console.log('exitCancel', msg);
        showAlert(t('notifications.exitCancel', { pair: msg.pair, reason: msg.reason }), 'warning', botname);
        break;
      case FtWsMessageTypes.entryCancel:
        console.log('entryCancel', msg);
        showAlert(t('notifications.entryCancel', { pair: msg.pair, reason: msg.reason }), 'warning', botname);
        break;
    }
  } else {
    console.log(`${botname}: Message ${msg.type} not shown.`);
  }
}
