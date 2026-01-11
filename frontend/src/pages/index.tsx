import Link from 'next/link';
import { useAuth } from '@/hooks/useAuth';
import { useEffect, useState } from 'react';
import { useRouter } from 'next/router';

const demoMessages = [
  { type: 'user', text: 'I need to report a workplace incident' },
  { type: 'ai', text: "🟢 I've identified that you want to fill an <strong>Incident Report</strong><br/><br/>Let's get started. What is your name?", confidence: 95 },
  { type: 'user', text: 'John Silva, phone (11) 98765-4321, email john@company.com' },
  { type: 'ai', text: "✅ Perfect! I've captured:<br/>• Name: John Silva<br/>• Phone: (11) 98765-4321<br/>• Email: john@company.com<br/><br/>Now, where did the incident occur?" },
];

export default function Home() {
  const { user } = useAuth();
  const router = useRouter();
  const [mounted, setMounted] = useState(false);
  const [messages, setMessages] = useState<{ type: string, text: string, confidence?: number }[]>([
    { type: 'ai', text: "Hi! I'm your FormFlow AI assistant. What would you like to do today?" }
  ]);
  const [isTyping, setIsTyping] = useState(false);
  const [demoIndex, setDemoIndex] = useState(0);

  useEffect(() => {
    setMounted(true);
  }, []);

  // Redirect logged-in users
  useEffect(() => {
    if (user) {
      router.push(user.role === 'admin' ? '/admin' : '/dashboard');
    }
  }, [user, router]);

  // Animated chat demo
  useEffect(() => {
    if (!mounted) return;

    const timer = setTimeout(() => {
      if (demoIndex < demoMessages.length) {
        const msg = demoMessages[demoIndex];

        if (msg.type === 'ai') {
          setIsTyping(true);
          setTimeout(() => {
            setIsTyping(false);
            setMessages(prev => [...prev, msg]);
            setDemoIndex(prev => prev + 1);
          }, 1200);
        } else {
          setMessages(prev => [...prev, msg]);
          setDemoIndex(prev => prev + 1);
        }
      } else {
        // Reset demo after completion
        setTimeout(() => {
          setMessages([{ type: 'ai', text: "Hi! I'm your FormFlow AI assistant. What would you like to do today?" }]);
          setDemoIndex(0);
        }, 4000);
      }
    }, demoIndex === 0 ? 2000 : 1500);

    return () => clearTimeout(timer);
  }, [mounted, demoIndex]);

  if (user) {
    return (
      <div className="min-h-screen flex items-center justify-center" style={{ background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)' }}>
        <div className="w-12 h-12 rounded-xl bg-white/20 flex items-center justify-center animate-pulse">
          <span className="text-2xl">🤖</span>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen overflow-x-hidden" style={{ background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)' }}>
      <div className="max-w-6xl mx-auto px-5">
        {/* Navbar */}
        <nav className="flex justify-between items-center py-5">
          <div className="flex items-center gap-2.5 text-white">
            <span className="text-3xl">🤖</span>
            <span className="text-2xl font-bold">FormFlow AI</span>
          </div>
          <div className="flex gap-4">
            <Link
              href="/login"
              className="px-6 py-3 rounded-lg font-semibold text-white bg-white/20 backdrop-blur-sm hover:bg-white/30 hover:-translate-y-0.5 transition-all"
            >
              Sign In
            </Link>
            <Link
              href="/register"
              className="px-6 py-3 rounded-lg font-semibold bg-white text-[#667eea] hover:-translate-y-0.5 hover:shadow-lg transition-all"
            >
              Get Started
            </Link>
          </div>
        </nav>

        {/* Hero */}
        <section className={`text-center py-20 text-white ${mounted ? 'animate-fade-in' : 'opacity-0'}`}>
          <h1 className="text-5xl md:text-6xl font-bold leading-tight mb-5">
            Fill Forms with<br />Natural Conversation
          </h1>
          <p className="text-2xl opacity-90 mb-10">
            AI-powered assistant that understands what you need and fills forms through chat
          </p>
          <div className="flex gap-5 justify-center flex-wrap">
            <Link
              href="/register"
              className="px-8 py-4 text-lg font-semibold rounded-lg bg-white text-[#667eea] hover:-translate-y-0.5 hover:shadow-xl transition-all"
            >
              Try Demo
            </Link>
            <button className="px-8 py-4 text-lg font-semibold rounded-lg bg-white/20 text-white backdrop-blur-sm hover:bg-white/30 hover:-translate-y-0.5 transition-all">
              Watch Video
            </button>
          </div>
        </section>

        {/* Chat Demo */}
        <div className={`bg-white/10 backdrop-blur-lg rounded-3xl p-10 my-16 border border-white/20 ${mounted ? 'animate-slide-up' : 'opacity-0'}`} style={{ animationDelay: '0.3s' }}>
          <div className="bg-white rounded-2xl p-8 max-w-3xl mx-auto shadow-2xl">
            <div className="space-y-5 max-h-80 overflow-y-auto">
              {messages.map((msg, i) => (
                <div key={i} className={`flex gap-3 ${msg.type === 'user' ? 'flex-row-reverse' : ''} animate-fade-in`}>
                  <div className={`w-10 h-10 rounded-full flex items-center justify-center text-xl flex-shrink-0 ${msg.type === 'ai'
                      ? 'bg-gradient-to-br from-[#667eea] to-[#764ba2]'
                      : 'bg-[#667eea]'
                    }`}>
                    {msg.type === 'ai' ? '🤖' : '👤'}
                  </div>
                  <div className={`max-w-[70%] px-5 py-4 rounded-2xl text-base leading-relaxed ${msg.type === 'ai'
                      ? 'bg-gray-100 text-gray-800'
                      : 'bg-[#667eea] text-white'
                    }`}>
                    <span dangerouslySetInnerHTML={{ __html: msg.text }} />
                    {msg.confidence && (
                      <span className="inline-block mt-2 px-3 py-1 rounded-full text-sm font-semibold bg-green-500 text-white">
                        {msg.confidence}% confidence
                      </span>
                    )}
                  </div>
                </div>
              ))}

              {isTyping && (
                <div className="flex gap-3 animate-fade-in">
                  <div className="w-10 h-10 rounded-full flex items-center justify-center text-xl bg-gradient-to-br from-[#667eea] to-[#764ba2]">
                    🤖
                  </div>
                  <div className="bg-gray-100 px-5 py-4 rounded-2xl">
                    <div className="flex gap-1">
                      <span className="w-2 h-2 rounded-full bg-gray-400 animate-bounce" style={{ animationDelay: '0ms' }} />
                      <span className="w-2 h-2 rounded-full bg-gray-400 animate-bounce" style={{ animationDelay: '150ms' }} />
                      <span className="w-2 h-2 rounded-full bg-gray-400 animate-bounce" style={{ animationDelay: '300ms' }} />
                    </div>
                  </div>
                </div>
              )}
            </div>
          </div>
        </div>

        {/* Features */}
        <section className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-8 py-16">
          {[
            { icon: '🧠', title: 'Smart Understanding', desc: 'AI automatically identifies which form you need and extracts information from natural conversation' },
            { icon: '⚡', title: 'Lightning Fast', desc: 'Fill complex forms in seconds instead of minutes. No more clicking through endless fields' },
            { icon: '🌐', title: 'Multi-Channel', desc: 'Use via web, WhatsApp, or API. Your forms, anywhere you need them' },
            { icon: '📊', title: 'Smart Reports', desc: 'Automated analytics and insights from your form responses with AI-powered analysis' },
          ].map((feature, i) => (
            <div
              key={feature.title}
              className={`bg-white/10 backdrop-blur-lg rounded-2xl p-8 border border-white/20 text-white hover:-translate-y-2 hover:bg-white/15 hover:shadow-xl transition-all ${mounted ? 'animate-slide-up' : 'opacity-0'}`}
              style={{ animationDelay: `${0.4 + i * 0.1}s` }}
            >
              <div className="text-5xl mb-4">{feature.icon}</div>
              <h3 className="text-xl font-bold mb-3">{feature.title}</h3>
              <p className="opacity-90 leading-relaxed">{feature.desc}</p>
            </div>
          ))}
        </section>

        {/* Footer */}
        <footer className="text-center py-10 text-white/70 border-t border-white/10">
          <p>© 2024 FormFlow AI. Built for productive teams.</p>
        </footer>
      </div>
    </div>
  );
}