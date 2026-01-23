'use client';

import { useState, useEffect } from 'react';
import { Bot, User, Mic, BookOpen, Sparkles, AlertCircle } from 'lucide-react';
import { cn } from '@/lib/utils';

interface Citation {
  index: number;
  source: string;
  title: string;
  relevance?: string;
}

interface SuggestedAction {
  type: string;
  command: string;
  description: string;
}

interface Message {
  role: 'user' | 'assistant';
  content: string;
  citations?: Citation[];
  suggestedActions?: SuggestedAction[];
  confidence?: number;
  timestamp: Date;
}

interface MinervaChatProps {
  patientName?: string;
  patientId?: string;
  className?: string;
}

const DEMO_STARTERS = [
  "What do you think about this patient?",
  "What's the differential diagnosis?",
  "Any drug interactions I should know about?",
  "What labs should I order?",
  "Explain the treatment guidelines",
];

export function MinervaChat({ patientName, patientId, className }: MinervaChatProps) {
  const [messages, setMessages] = useState<Message[]>([]);
  const [isListening, setIsListening] = useState(false);
  const [isSpeaking, setIsSpeaking] = useState(false);
  const EHR_PROXY_URL = process.env.NEXT_PUBLIC_EHR_PROXY_URL || 'http://localhost:8002';

  // Poll for Minerva activity (in real implementation, use WebSocket)
  useEffect(() => {
    const interval = setInterval(async () => {
      try {
        const response = await fetch(`${EHR_PROXY_URL}/api/v1/minerva/status`);
        if (response.ok) {
          const data = await response.json();
          setIsListening(data.is_listening || false);
          setIsSpeaking(data.is_speaking || false);
        }
      } catch {
        // Silently ignore polling errors
      }
    }, 2000);

    return () => clearInterval(interval);
  }, [EHR_PROXY_URL]);

  const sendMessage = async (message: string) => {
    // Add user message
    const userMessage: Message = {
      role: 'user',
      content: message,
      timestamp: new Date(),
    };
    setMessages((prev) => [...prev, userMessage]);

    try {
      const response = await fetch(`${EHR_PROXY_URL}/api/v1/minerva/chat`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          message,
          patient_id: patientId,
        }),
      });

      if (response.ok) {
        const data = await response.json();
        const assistantMessage: Message = {
          role: 'assistant',
          content: data.response,
          citations: data.citations,
          suggestedActions: data.suggested_actions,
          confidence: data.confidence,
          timestamp: new Date(),
        };
        setMessages((prev) => [...prev, assistantMessage]);
      }
    } catch (error) {
      console.error('Minerva chat error:', error);
    }
  };

  return (
    <div
      className={cn(
        'flex flex-col rounded-xl bg-white shadow-sm ring-1 ring-gray-900/5 dark:bg-gray-800 dark:ring-gray-800',
        className
      )}
    >
      {/* Header */}
      <div className="flex items-center justify-between border-b border-gray-200 px-4 py-3 dark:border-gray-700">
        <div className="flex items-center gap-3">
          <div className="relative">
            <div className="flex h-10 w-10 items-center justify-center rounded-full bg-gradient-to-br from-purple-500 to-indigo-600">
              <Bot className="h-5 w-5 text-white" />
            </div>
            {(isListening || isSpeaking) && (
              <span className="absolute -right-0.5 -top-0.5 flex h-3 w-3">
                <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-green-400 opacity-75"></span>
                <span className="relative inline-flex h-3 w-3 rounded-full bg-green-500"></span>
              </span>
            )}
          </div>
          <div>
            <h3 className="text-sm font-semibold text-gray-900 dark:text-white">Minerva</h3>
            <p className="text-xs text-gray-500 dark:text-gray-400">
              {isSpeaking ? 'Speaking...' : isListening ? 'Listening...' : 'Ready'}
            </p>
          </div>
        </div>
        {patientName && (
          <div className="flex items-center gap-2 rounded-full bg-mdx-primary/10 px-3 py-1">
            <User className="h-3 w-3 text-mdx-primary" />
            <span className="text-xs font-medium text-mdx-primary">{patientName}</span>
          </div>
        )}
      </div>

      {/* Messages */}
      <div className="flex-1 space-y-4 overflow-y-auto p-4" style={{ maxHeight: '400px' }}>
        {messages.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-8 text-center">
            <Sparkles className="mb-3 h-8 w-8 text-purple-500" />
            <p className="text-sm font-medium text-gray-900 dark:text-white">
              Say &quot;Hey Minerva&quot; to start
            </p>
            <p className="mt-1 text-xs text-gray-500 dark:text-gray-400">
              Or try one of these questions:
            </p>
            <div className="mt-4 flex flex-wrap justify-center gap-2">
              {DEMO_STARTERS.slice(0, 3).map((starter) => (
                <button
                  key={starter}
                  onClick={() => sendMessage(starter)}
                  className="rounded-full bg-gray-100 px-3 py-1.5 text-xs font-medium text-gray-700 transition-colors hover:bg-gray-200 dark:bg-gray-700 dark:text-gray-300 dark:hover:bg-gray-600"
                >
                  {starter}
                </button>
              ))}
            </div>
          </div>
        ) : (
          messages.map((msg, idx) => (
            <div
              key={idx}
              className={cn(
                'flex gap-3',
                msg.role === 'user' ? 'flex-row-reverse' : 'flex-row'
              )}
            >
              <div
                className={cn(
                  'flex h-8 w-8 flex-shrink-0 items-center justify-center rounded-full',
                  msg.role === 'user'
                    ? 'bg-mdx-primary/20'
                    : 'bg-gradient-to-br from-purple-500 to-indigo-600'
                )}
              >
                {msg.role === 'user' ? (
                  <Mic className="h-4 w-4 text-mdx-primary" />
                ) : (
                  <Bot className="h-4 w-4 text-white" />
                )}
              </div>
              <div
                className={cn(
                  'max-w-[80%] rounded-xl px-4 py-2',
                  msg.role === 'user'
                    ? 'bg-mdx-primary text-white'
                    : 'bg-gray-100 text-gray-900 dark:bg-gray-700 dark:text-white'
                )}
              >
                <p className="text-sm">{msg.content}</p>

                {/* Citations */}
                {msg.citations && msg.citations.length > 0 && (
                  <div className="mt-2 border-t border-gray-200 pt-2 dark:border-gray-600">
                    <div className="flex items-center gap-1 text-xs text-gray-500 dark:text-gray-400">
                      <BookOpen className="h-3 w-3" />
                      <span>Sources:</span>
                    </div>
                    <div className="mt-1 space-y-1">
                      {msg.citations.map((citation) => (
                        <p
                          key={citation.index}
                          className="text-xs text-gray-600 dark:text-gray-400"
                        >
                          [{citation.index}] {citation.source}: {citation.title}
                        </p>
                      ))}
                    </div>
                  </div>
                )}

                {/* Suggested Actions */}
                {msg.suggestedActions && msg.suggestedActions.length > 0 && (
                  <div className="mt-2 flex flex-wrap gap-1">
                    {msg.suggestedActions.map((action, actionIdx) => (
                      <span
                        key={actionIdx}
                        className="inline-flex items-center rounded bg-purple-100 px-2 py-0.5 text-xs font-medium text-purple-800 dark:bg-purple-900/30 dark:text-purple-300"
                      >
                        Say &quot;{action.command}&quot;
                      </span>
                    ))}
                  </div>
                )}

                {/* Confidence indicator */}
                {msg.confidence !== undefined && (
                  <div className="mt-2 flex items-center gap-2">
                    <div className="h-1 flex-1 rounded-full bg-gray-200 dark:bg-gray-600">
                      <div
                        className="h-1 rounded-full bg-green-500"
                        style={{ width: `${msg.confidence * 100}%` }}
                      />
                    </div>
                    <span className="text-xs text-gray-500">
                      {Math.round(msg.confidence * 100)}%
                    </span>
                  </div>
                )}
              </div>
            </div>
          ))
        )}
      </div>

      {/* Voice indicator */}
      {isListening && (
        <div className="flex items-center justify-center gap-2 border-t border-gray-200 bg-green-50 px-4 py-3 dark:border-gray-700 dark:bg-green-900/20">
          <div className="flex gap-1">
            <span className="h-2 w-2 animate-bounce rounded-full bg-green-500" style={{ animationDelay: '0ms' }} />
            <span className="h-2 w-2 animate-bounce rounded-full bg-green-500" style={{ animationDelay: '150ms' }} />
            <span className="h-2 w-2 animate-bounce rounded-full bg-green-500" style={{ animationDelay: '300ms' }} />
          </div>
          <span className="text-sm font-medium text-green-700 dark:text-green-400">
            Minerva is listening...
          </span>
        </div>
      )}

      {/* Speaking indicator */}
      {isSpeaking && !isListening && (
        <div className="flex items-center justify-center gap-2 border-t border-gray-200 bg-purple-50 px-4 py-3 dark:border-gray-700 dark:bg-purple-900/20">
          <AlertCircle className="h-4 w-4 text-purple-600" />
          <span className="text-sm font-medium text-purple-700 dark:text-purple-400">
            Minerva is speaking...
          </span>
        </div>
      )}
    </div>
  );
}
