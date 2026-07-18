import Link from 'next/link';
import { useAuth } from '@/hooks/useAuth';
import { useEffect, useState } from 'react';
import { useRouter } from 'next/router';

// Demo stages for the interactive wizard
const DEMO_STAGES = [
  { 
    aiQuestion: "Hi! I'm your FormFlow AI. What do you need to do?", 
    userInput: "", 
    isTyping: false,
    formState: { name: "", phone: "", email: "", location: "" }
  },
  { 
    aiQuestion: "Hi! I'm your FormFlow AI. What do you need to do?", 
    userInput: "I need to report a workplace incident", 
    isTyping: true,
    formState: { name: "", phone: "", email: "", location: "" }
  },
  { 
    aiQuestion: "I'll help you file an Incident Report. What is your contact information?", 
    userInput: "", 
    isTyping: false,
    formState: { name: "", phone: "", email: "", location: "" },
    highlightForm: true
  },
  { 
    aiQuestion: "I'll help you file an Incident Report. What is your contact information?", 
    userInput: "John Silva, phone (11) 98765-4321, email john@company.com", 
    isTyping: true,
    formState: { name: "", phone: "", email: "", location: "" },
    highlightForm: true
  },
  { 
    aiQuestion: "Got it. Where exactly did the incident occur?", 
    userInput: "", 
    isTyping: false,
    formState: { name: "John Silva", phone: "(11) 98765-4321", email: "john@company.com", location: "" },
    flashFields: ["name", "phone", "email"]
  },
  { 
    aiQuestion: "Got it. Where exactly did the incident occur?", 
    userInput: "In the main warehouse, near loading dock 3", 
    isTyping: true,
    formState: { name: "John Silva", phone: "(11) 98765-4321", email: "john@company.com", location: "" }
  },
  { 
    aiQuestion: "Incident reported successfully! The safety team has been notified.", 
    userInput: "", 
    isTyping: false,
    formState: { name: "John Silva", phone: "(11) 98765-4321", email: "john@company.com", location: "Main warehouse, loading dock 3" },
    flashFields: ["location"],
    isComplete: true
  }
];

export default function Home() {
  const { user } = useAuth();
  const router = useRouter();
  const [mounted, setMounted] = useState(false);
  
  // Interactive Wizard State
  const [demoIndex, setDemoIndex] = useState(0);
  const [typedInput, setTypedInput] = useState("");

  useEffect(() => {
    setMounted(true);
  }, []);

  // Redirect logged-in users
  useEffect(() => {
    if (user) {
      router.push(user.role === 'admin' ? '/admin' : '/dashboard');
    }
  }, [user, router]);

  // Typewriter effect for user input
  useEffect(() => {
    if (!mounted) return;
    
    const currentStage = DEMO_STAGES[demoIndex];
    
    if (currentStage.isTyping) {
      let charIndex = 0;
      setTypedInput("");
      const typeInterval = setInterval(() => {
        if (charIndex <= currentStage.userInput.length) {
          setTypedInput(currentStage.userInput.substring(0, charIndex));
          charIndex++;
        } else {
          clearInterval(typeInterval);
          setTimeout(() => setDemoIndex(prev => prev + 1), 600);
        }
      }, 40); // typing speed
      
      return () => clearInterval(typeInterval);
    } else {
      setTypedInput(currentStage.userInput);
      const stageDelay = currentStage.isComplete ? 4000 : 1800;
      
      const timer = setTimeout(() => {
        if (demoIndex < DEMO_STAGES.length - 1) {
          setDemoIndex(prev => prev + 1);
        } else {
          setDemoIndex(0); // Loop demo
        }
      }, stageDelay);
      
      return () => clearTimeout(timer);
    }
  }, [demoIndex, mounted]);

  if (user) {
    return (
      <div className="min-h-screen flex items-center justify-center" style={{ background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)' }}>
        <div className="w-12 h-12 rounded-xl bg-white/20 flex items-center justify-center animate-pulse">
          <div className="w-6 h-6 border-2 border-white rounded-full border-t-transparent animate-spin"></div>
        </div>
      </div>
    );
  }

  const currentStage = DEMO_STAGES[demoIndex];

  return (
    <div className="min-h-screen overflow-x-hidden font-sans" style={{ background: 'linear-gradient(135deg, #0f172a 0%, #1e1b4b 100%)' }}>
      <div className="max-w-7xl mx-auto px-6">
        {/* Navbar */}
        <nav className="flex justify-between items-center py-6">
          <div className="flex items-center gap-3 text-white">
            <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-indigo-500 to-purple-600 flex items-center justify-center shadow-lg shadow-indigo-500/30">
              <span className="text-xl font-bold">FF</span>
            </div>
            <span className="text-2xl font-bold tracking-tight">FormFlow</span>
          </div>
          <div className="flex gap-4">
            <Link
              href="/login"
              className="px-6 py-2.5 rounded-full font-medium text-white/90 hover:text-white hover:bg-white/10 transition-colors"
            >
              Sign In
            </Link>
            <Link
              href="/register"
              className="px-6 py-2.5 rounded-full font-medium bg-white text-indigo-950 hover:shadow-lg hover:shadow-white/20 hover:-translate-y-0.5 transition-all"
            >
              Get Started
            </Link>
          </div>
        </nav>

        {/* Hero & Interactive Wizard */}
        <section className={`pt-24 pb-20 ${mounted ? 'animate-fade-in' : 'opacity-0'}`}>
          <div className="text-center max-w-4xl mx-auto mb-16">
            <h1 className="text-5xl md:text-7xl font-extrabold text-transparent bg-clip-text bg-gradient-to-r from-white via-indigo-100 to-indigo-300 leading-tight mb-6 tracking-tight">
              Fill complex forms<br />like a conversation.
            </h1>
            <p className="text-xl md:text-2xl text-indigo-200/80 font-light mb-10 max-w-2xl mx-auto">
              The AI-powered intelligent interface that understands context, extracts data, and eliminates manual data entry forever.
            </p>
          </div>

          {/* SPLIT SCREEN WIZARD DEMO */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-8 max-w-6xl mx-auto items-center">
            
            {/* Left: Conversational UI */}
            <div className="flex flex-col justify-center pr-0 lg:pr-10 relative z-10">
              <div className="mb-10 transition-all duration-500 ease-out transform" key={currentStage.aiQuestion}>
                <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-indigo-500/20 border border-indigo-500/30 text-indigo-300 text-sm font-medium mb-6">
                  <span className="w-2 h-2 rounded-full bg-indigo-400 animate-pulse"></span>
                  FormFlow AI
                </div>
                <h2 className="text-3xl md:text-4xl font-semibold text-white leading-tight animate-slide-up">
                  {currentStage.aiQuestion}
                </h2>
              </div>
              
              <div className="relative group">
                <div className="absolute -inset-1 bg-gradient-to-r from-indigo-500 to-purple-600 rounded-2xl blur opacity-25 group-hover:opacity-40 transition duration-1000 group-hover:duration-200"></div>
                <div className="relative bg-[#0f172a]/80 backdrop-blur-xl border border-white/10 rounded-2xl p-2 flex items-center">
                  <input 
                    type="text" 
                    readOnly 
                    value={typedInput}
                    placeholder="Type your answer naturally..."
                    className="w-full bg-transparent border-none outline-none text-white text-lg px-4 py-3 placeholder-white/30 font-light"
                  />
                  <div className={`w-10 h-10 rounded-xl flex items-center justify-center flex-shrink-0 transition-colors ${currentStage.isTyping ? 'bg-indigo-600 text-white' : 'bg-white/5 text-white/30'}`}>
                    <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><line x1="22" y1="2" x2="11" y2="13"></line><polygon points="22 2 15 22 11 13 2 9 22 2"></polygon></svg>
                  </div>
                </div>
              </div>
            </div>

            {/* Right: Smart Form Visualizer */}
            <div className={`relative rounded-3xl p-1 bg-gradient-to-b from-white/15 to-white/5 backdrop-blur-2xl shadow-2xl shadow-indigo-900/50 transition-all duration-700 ${currentStage.highlightForm ? 'ring-2 ring-indigo-400/50 shadow-indigo-500/30' : ''}`}>
              
              {/* Form Header */}
              <div className="bg-[#1e293b]/90 rounded-[23px] overflow-hidden">
                <div className="px-6 py-4 border-b border-white/10 flex justify-between items-center bg-white/5">
                  <div className="flex items-center gap-2">
                    <svg className="w-5 h-5 text-indigo-400" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" /></svg>
                    <span className="text-white font-medium">Incident Report</span>
                  </div>
                  <span className={`text-xs px-2 py-1 rounded-md ${currentStage.isComplete ? 'bg-green-500/20 text-green-400 border border-green-500/30' : 'bg-white/10 text-white/60'}`}>
                    {currentStage.isComplete ? 'Completed' : 'Drafting...'}
                  </span>
                </div>
                
                {/* Form Fields */}
                <div className="p-6 space-y-5">
                  {[
                    { id: 'name', label: 'Full Name', value: currentStage.formState.name, placeholder: 'Jane Doe' },
                    { id: 'phone', label: 'Phone Number', value: currentStage.formState.phone, placeholder: '+1 (555) 000-0000' },
                    { id: 'email', label: 'Email Address', value: currentStage.formState.email, placeholder: 'jane@example.com' },
                    { id: 'location', label: 'Incident Location', value: currentStage.formState.location, placeholder: 'Specific area of occurrence' },
                  ].map((field) => (
                    <div key={field.id} className="relative">
                      <label className="block text-xs font-medium text-indigo-300/70 mb-1.5 uppercase tracking-wider">{field.label}</label>
                      <div className={`w-full px-4 py-2.5 rounded-lg border flex items-center transition-all duration-500 ${field.value ? 'bg-indigo-500/10 border-indigo-500/30' : 'bg-white/5 border-white/10'} ${currentStage.flashFields?.includes(field.id) ? 'bg-indigo-500/40 border-indigo-400 ring-2 ring-indigo-400/50' : ''}`}>
                        {field.value ? (
                          <span className="text-white font-medium animate-fade-in">{field.value}</span>
                        ) : (
                          <span className="text-white/20 italic text-sm">{field.placeholder}</span>
                        )}
                        {field.value && currentStage.flashFields?.includes(field.id) && (
                           <span className="ml-auto flex h-2 w-2 relative">
                             <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-indigo-400 opacity-75"></span>
                             <span className="relative inline-flex rounded-full h-2 w-2 bg-indigo-500"></span>
                           </span>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            </div>
            
          </div>
        </section>

        {/* Features */}
        <section className="grid grid-cols-1 md:grid-cols-3 gap-6 py-20 border-t border-white/10 mt-10">
          {[
            { icon: '🎯', title: 'Contextual Extraction', desc: 'Stop building rigid UI forms. The AI extracts exact parameters from natural sentences.' },
            { icon: '⚡', title: 'Frictionless UX', desc: 'Reduce drop-off rates by 80%. Users chat naturally, and structured data is generated instantly.' },
            { icon: '🔗', title: 'API & Integrations', desc: 'Connect to your existing CRM, ERP, or internal database with zero boilerplate code.' },
          ].map((feature, i) => (
            <div
              key={feature.title}
              className={`rounded-2xl p-8 transition-all duration-500 ${mounted ? 'animate-slide-up opacity-100' : 'opacity-0 translate-y-10'}`}
              style={{ transitionDelay: `${0.2 + i * 0.15}s` }}
            >
              <div className="w-12 h-12 rounded-xl bg-indigo-500/10 flex items-center justify-center text-2xl mb-6 border border-indigo-500/20">
                {feature.icon}
              </div>
              <h3 className="text-xl font-semibold text-white mb-3 tracking-tight">{feature.title}</h3>
              <p className="text-indigo-200/70 leading-relaxed font-light">{feature.desc}</p>
            </div>
          ))}
        </section>

        {/* Footer */}
        <footer className="text-center py-10 text-indigo-300/50 border-t border-white/5 font-light text-sm">
          <p>© 2024 FormFlow AI. Redefining data entry.</p>
        </footer>
      </div>
    </div>
  );
}