/**
 * Tailwind CSS 4 + Spark Design 配置
 * Spark Design 自带完整 token + utility（import 'sparkdesign/style'），我们额外追加
 * MSR 自定义语义令牌（颜色 / 间距 / 圆角 / 阴影），全部以 CSS 变量驱动以保持一致。
 */
export default {
  plugins: {
    '@tailwindcss/postcss': {},
    autoprefixer: {},
  },
};