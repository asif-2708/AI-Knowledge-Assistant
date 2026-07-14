import { HttpClient } from '@angular/common/http';
import { Injectable } from '@angular/core';
import { Observable } from 'rxjs';
import { environment } from '../../environments/environment';
import { AuthService } from './auth.service';

export interface ChatMessage {
  question: string;
  answer: string;
  timestamp: string;
}

interface ChatResponse {
  answer: string;
}

@Injectable({ providedIn: 'root' })
export class ChatService {
  private apiUrl = environment.apiUrl;

  constructor(private http: HttpClient, private authService: AuthService) {}

  query(question: string): Observable<ChatResponse> {
    return this.http.post<ChatResponse>(`${this.apiUrl}/chat/query`, { question });
  }

  queryStream(question: string): Observable<string> {
    return new Observable<string>((observer) => {
      const token = sessionStorage.getItem('ai_knowledge_token');
      const controller = new AbortController();

      fetch(`${this.apiUrl}/chat/stream?question=${encodeURIComponent(question)}`, {
        headers: {
          'Authorization': `Bearer ${token}`
        },
        signal: controller.signal
      }).then(async (response) => {
        if (response.status === 401) {
          console.warn('[ChatService] 401 Unauthorized detected! Clearing token and reloading...');
          sessionStorage.removeItem('ai_knowledge_token');
          window.location.reload();
          throw new Error('Unauthorized');
        }
        if (!response.ok) {
          throw new Error(`HTTP error! status: ${response.status}`);
        }
        const reader = response.body?.getReader();
        if (!reader) {
          throw new Error('No readable stream available');
        }

        const decoder = new TextDecoder();
        try {
          while (true) {
            const { value, done } = await reader.read();
            if (done) {
              break;
            }
            const chunk = decoder.decode(value, { stream: true });
            if (chunk) {
              observer.next(chunk);
            }
          }
          observer.complete();
        } catch (err) {
          observer.error(err);
        }
      }).catch((err) => {
        observer.error(err);
      });

      return () => {
        controller.abort();
      };
    });
  }

  private getHistoryKey(): string {
    const username = this.authService.getUsername();
    return username ? `ai_knowledge_chat_history_${username}` : 'ai_knowledge_chat_history_guest';
  }

  getHistory(): ChatMessage[] {
    try {
      const key = this.getHistoryKey();
      const data = localStorage.getItem(key);
      return data ? JSON.parse(data) : [];
    } catch (e) {
      console.error('Error parsing chat history:', e);
      return [];
    }
  }

  saveToHistory(question: string, answer: string): void {
    const key = this.getHistoryKey();
    const history = this.getHistory();
    history.unshift({ question, answer, timestamp: new Date().toISOString() });
    localStorage.setItem(key, JSON.stringify(history));
  }

  clearHistory(): void {
    const key = this.getHistoryKey();
    localStorage.removeItem(key);
  }

  deleteFromHistory(index: number): void {
    const key = this.getHistoryKey();
    const history = this.getHistory();
    if (index >= 0 && index < history.length) {
      history.splice(index, 1);
      localStorage.setItem(key, JSON.stringify(history));
    }
  }
}
