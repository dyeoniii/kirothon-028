import { useEffect, useState } from 'react';
import { useLocation } from 'react-router-dom';

export default function App() {
  const location = useLocation();
  const [url, setUrl] = useState('');
  useEffect(() => {
    if (location.pathname === '/share-target') {
      const params = new URLSearchParams(location.search);
      const value = params.get('url') || params.get('text') || '';
      // The FE session will implement robust shared URL extraction and validation.
      setUrl(value);
    }
  }, [location]);
  return <main className="mx-auto max-w-3xl px-5 py-14">
    <p className="text-sm font-bold tracking-widest text-indigo-600">CATCH TROLLS</p>
    <h1 className="mt-3 text-3xl font-bold">Catch Trolls</h1>
    <p className="mt-3 text-slate-600">악플 분석부터 증거 정리까지. 현재는 개발 시작용 화면입니다.</p>
    <section className="mt-8 rounded-xl border bg-white p-6 shadow-sm">
      <h2 className="font-semibold">SNS URL 입력</h2>
      <input aria-label="SNS URL" className="mt-3 w-full rounded border p-3" placeholder="https://www.youtube.com/watch?v=..." value={url} onChange={e => setUrl(e.target.value)} />
      <p className="mt-3 text-sm text-slate-500">기능 구현 전입니다. Kiro Crew S1에서 완성합니다.</p>
    </section>
  </main>;
}
