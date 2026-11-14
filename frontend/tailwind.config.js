/** @type {import('tailwindcss').Config} */
// 색상 값은 src/index.css 의 CSS 변수(디자인 토큰)가 정의합니다. 여기서는 이름만 연결합니다.
const token = (name) => `rgb(var(--${name}) / <alpha-value>)`;
const scale = (prefix, steps) => Object.fromEntries(steps.map((s) => [s, token(`${prefix}-${s}`)]));

export default {
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  theme: {
    extend: {
      fontFamily: {
        sans: ['Pretendard Variable', 'Pretendard', '-apple-system', 'BlinkMacSystemFont', 'Apple SD Gothic Neo', 'Noto Sans KR', 'system-ui', 'sans-serif'],
      },
      boxShadow: {
        card: 'var(--shadow-card)',
      },
      borderRadius: {
        card: 'var(--radius-card)',
        ctl: 'var(--radius-ctl)',
      },
      colors: {
        canvas: token('canvas'),
        brand: scale('brand', [50, 100, 200, 300, 400, 500, 600, 700, 800]),
        ink: scale('ink', [50, 100, 200, 300, 400, 500, 600, 700, 800, 900]),
      },
    },
  },
  plugins: [],
};
