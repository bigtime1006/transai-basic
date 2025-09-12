import { createI18n } from 'vue-i18n';
import en from './locales/en.json';
import zh from './locales/zh.json';
import ja from './locales/ja.json';
import ko from './locales/ko.json';

const messages = {
  en,
  zh,
  ja,
  ko
};

const i18n = createI18n({
  legacy: false, // use Composition API
  locale: 'zh', // set default locale
  fallbackLocale: 'en', // fallback locale
  messages,
});

export default i18n;
